import cv2
import requests
import time
import os
import sys
from auth_ui import authenticate_ui
from playsound3 import playsound


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from camera.camera_thread import camera
import threading
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIG =================
BASE_SERVER = "http://127.0.0.1:9090"
SERVER_URL = f"{BASE_SERVER}/status"
API_HEADERS = {
    "x-api-key": "gaurav_secure_123"
}

BOT_TOKEN = "<telegram-bot-token>"
CHAT_ID = "<chat-id>"

PRIORITY_MOTION = 1
PRIORITY_AUTH = 3

alarm_active = False
_last_wrong_thread = None  # ← ADD THIS

# ==========================================

attempt_count = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "..", "images")
VIDEO_PATH = os.path.join(BASE_DIR, "..", "videos")
LOG_PATH = os.path.join(BASE_DIR, "..", "logs", "activity.txt")
ALARM_FILE = os.path.join(BASE_DIR, "..", "alarm.mp3")

os.makedirs(IMAGE_PATH, exist_ok=True)
os.makedirs(VIDEO_PATH, exist_ok=True)          
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

alarm_active = False

# ================= PRIORITY HELPERS =================


def acquire_camera(priority, name):
    try:
        r = requests.get(
            f"{BASE_SERVER}/camera/acquire/{priority}/{name}",
            headers=API_HEADERS,
            timeout=2
        ).json()

        print(f"📷 Acquired camera — {name} (priority {priority}) granted={r['granted']}")
    except Exception as e:
        print(f"⚠️ acquire_camera error: {e}")


def release_camera_api(priority, name):
    try:
        requests.get(
            f"{BASE_SERVER}/camera/release/{priority}/{name}",
            headers=API_HEADERS,
            timeout=2
        )
        print(f"📷 Released camera — {name}")
    except Exception as e:
        print(f"⚠️ release_camera error: {e}")


def can_motion_run():
    try:
        r = requests.get(
            f"{BASE_SERVER}/camera/priority",
            headers=API_HEADERS,
            timeout=1
        ).json()

        return r.get("can_motion_run", True)
    except:
        return True


# ================= FUNCTIONS =================


def log_event(msg):
    with open(LOG_PATH, "a") as f:
        f.write(f"{time.ctime()} - {msg}\n")


def send_telegram_alert(image_path, message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(image_path, "rb") as img:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": message},
                files={"photo": img},
                timeout=10,
                verify=False,
            )
        print("📱 Telegram image sent")
    except Exception as e:
        print("⚠️ Telegram error:", e)

def send_video(video_path):
    try:
        if video_path is None:
            print("⚠️ No video path to send")
            return
        if not os.path.exists(video_path):
            print(f"⚠️ Video file missing: {video_path}")
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
        with open(video_path, "rb") as vid:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID},
                files={"video": vid},
                timeout=30,
                verify=False,
            )
        print("📱 Telegram video sent")
    except Exception as e:
        print("⚠️ Video error:", e)
def play_alarm():
    global alarm_active
    if not alarm_active:
        alarm_active = True
        try:
            playsound(ALARM_FILE)
        except Exception as e:
            print("⚠️ Alarm error:", e)
        alarm_active = False


def record_videoS(duration=4):
    # detect real frame size first
    frame = None
    for _ in range(60):
        frame = camera.get_frame()
        if frame is not None:
            break
        time.sleep(0.05)

    if frame is None:
        print("⚠️ No frame for video recording")
        return None

    h, w = frame.shape[:2]
    filename = os.path.join(VIDEO_PATH, f"video_{int(time.time())}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))

    start = time.time()
    while time.time() - start < duration:
        f = camera.get_frame()
        if f:
            t = threading.Thread(          # ← WRONG: spawning threads inside record loop
                target=lambda: send_video(record_video()),  # ← WRONG: recursive!
                daemon=False,
            )
            t.start()
            t.join(timeout=30)
    if frame_count == 0:
        try:
            os.remove(filename)
        except OSError:
            pass
        return None

    return filename

def open_video_writer(base_name, w, h, fps=20.0):
    candidates = [
        ("avc1", "mp4"),
        ("H264", "mp4"),
        ("mp4v", "mp4"),
    ]

    for fourcc, ext in candidates:
        filename = os.path.join(VIDEO_PATH, f"{base_name}.{ext}")
        out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
        if out.isOpened():
            return out, filename, fourcc

    return None, None, None


def record_video(duration=4):
    print("🎥 record_video() called")
    frame = None
    for _ in range(60):
        frame = camera.get_frame()
        if frame is not None:
            break
        time.sleep(0.05)

    if frame is None:
        print("⚠️ record_video: No frame available")
        return None

    h, w = frame.shape[:2]
    print(f"🎥 Frame size: {w}x{h}")
    
    base_name = f"video_{int(time.time())}"
    out, filename, codec = open_video_writer(base_name, w, h, fps=20.0)
    print(f"🎥 Saving to: {filename}")
    print(f"🎥 VIDEO_PATH exists: {os.path.exists(VIDEO_PATH)}")
    print(f"🎥 VideoWriter opened: {bool(out)} codec={codec}")

    if not out:
        print("⚠️ No supported video codec available for MP4 recording")
        return None

    frame_count = 0
    start = time.time()
    while time.time() - start < duration:
        f = camera.get_frame()
        if f is not None:
            out.write(f)
            frame_count += 1
        time.sleep(0.05)

    out.release()
    print(f"🎥 Frames written: {frame_count}")
    print(f"🎥 File exists after release: {os.path.exists(filename)}")
    print(f"🎥 File size: {os.path.getsize(filename) if os.path.exists(filename) else 'N/A'} bytes")

    if frame_count == 0:
        try:
            os.remove(filename)
        except OSError:
            pass
        return None

    return filename

def capture_and_alert(filename_prefix, message, log_msg, alarm=False):
    frame = None
    for _ in range(60):
        frame = camera.get_frame()
        if frame is not None:
            break
        time.sleep(0.05)

    if frame is not None:
        filename = os.path.abspath(os.path.join(IMAGE_PATH, f"{filename_prefix}_{int(time.time())}.jpg"))
        saved = cv2.imwrite(filename, frame)
        print(f"📸 Image saved: {saved} → {filename}")
        if not saved:
            print(f"❌ cv2.imwrite FAILED — path: {os.path.dirname(filename)}")
        threading.Thread(target=send_telegram_alert, args=(filename, message), daemon=True).start()
        log_event(log_msg)
        if alarm:
            threading.Thread(target=play_alarm, daemon=True).start()
        return filename
    else:
        log_event(f"{log_msg} — no frame available")
        print(f"⚠️ No frame available for {filename_prefix}")
        return None

# ================= AUTH CALLBACKS =================


def on_wrong_password(attempt_num):
    global _last_wrong_thread
    print(f"🔐 on_wrong_password called — attempt {attempt_num}")

    def _run():
        print("🔐 _run thread started")
        next_wait = min(attempt_num * 5, 30)
        msg = (
            f"🔐 WRONG PASSWORD 🔐\n"
            f"🕒 {time.ctime()}\n"
            f"❌ Attempt #{attempt_num}\n"
            f"⏳ Next cooldown: {next_wait}s"
        )
        print("📸 Calling capture_and_alert...")
        capture_and_alert(
            filename_prefix="auth_fail",
            message=msg,
            log_msg=f"Wrong password attempt #{attempt_num}",
            alarm=True,
        )
        print("📸 capture_and_alert done — starting record_video")
        video = record_video(duration=4)
        print(f"🎥 record_video returned: {video}")
        if video:
            print("📤 Calling send_video...")
            send_video(video)
            print("📤 send_video done")
        else:
            print("⚠️ No video to send")

    _last_wrong_thread = threading.Thread(target=_run, daemon=False)
    _last_wrong_thread.start()
    print(f"🔐 _last_wrong_thread started: {_last_wrong_thread.name}")

def on_fail_start():
    global _last_wrong_thread
    print("⏳ Waiting for capture+video to finish...")
    if _last_wrong_thread and _last_wrong_thread.is_alive():
        _last_wrong_thread.join(timeout=40)  # photo(5s) + video(4s) + upload(15s)
    print("✅ Stopping camera now")
    camera.stop_capture()
    release_camera_api(PRIORITY_AUTH, "auth_capture")


def on_fail_end():
    """
    User clicked Start after cooldown — restart camera and re-acquire priority.
    """
    acquire_camera(PRIORITY_AUTH, "auth_capture")  # ← tell server first
    camera.start_capture()  # ← start local hardware
    camera.wait_for_frame(timeout=5)  # ← wait until frames flow


# ================= START =================

# Tell server we need camera at AUTH priority
acquire_camera(PRIORITY_AUTH, "auth_capture")

# Start local camera hardware
camera.start_capture()

# Wait for first frame before showing auth UI
print("⏳ Waiting for camera...")
if not camera.wait_for_frame(timeout=10):
    print("⚠️ Camera slow to start — continuing anyway")
else:
    print("✅ Camera ready")

# 🔐 AUTH UI
auth_passed = authenticate_ui(
    on_fail_start=on_fail_start,
    on_fail_end=on_fail_end,
    on_wrong_password=on_wrong_password,
)

if not auth_passed:
    print("🚨 Unauthorized access — all attempts failed!")

    # Camera may have been stopped during last cooldown — restart it
    acquire_camera(PRIORITY_AUTH, "auth_capture")
    camera.start_capture()  # ← restart after cooldown
    camera.wait_for_frame(timeout=5)

    msg = (
        f"🚨 UNAUTHORIZED ACCESS 🚨\n"
        f"🕒 {time.ctime()}\n"
        f"❌ All password attempts failed"
    )
    f = capture_and_alert(
        filename_prefix="intruder",
        message=msg,
        log_msg="Unauthorized access — all attempts failed",
        alarm=True,
    )
    if f:
        threading.Thread(target=lambda: send_video(record_video()), daemon=True).start()
        time.sleep(5)  # let video thread finish before exit

    camera.stop_capture()
    release_camera_api(PRIORITY_AUTH, "auth_capture")
    exit()

# Auth passed — stop auth camera, release server priority
camera.stop_capture()
release_camera_api(PRIORITY_AUTH, "auth_capture")

# ================= MONITOR =================

# Re-acquire at motion priority and restart camera
acquire_camera(PRIORITY_MOTION, "motion_detector")
camera.start_capture()  # ← fresh start for motion

if not camera.wait_for_frame(timeout=10):
    print("❌ Camera not available for motion detection")
    camera.stop_capture()
    release_camera_api(PRIORITY_MOTION, "motion_detector")
    exit()

# Wait until we have two valid frames
frame1 = None
frame2 = None

while frame1 is None:
    frame1 = camera.get_frame()
    time.sleep(0.05)

while frame2 is None:
    frame2 = camera.get_frame()
    time.sleep(0.05)

print("✅ System Running")

print("✅ System Running")

last_capture_time = 0
last_video_time = 0

try:
    while True:
        try:
            status = requests.get(SERVER_URL, timeout=2).json()
        except:
            status = {"system": "OFF"}

        if status["system"] == "ON" and can_motion_run():
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                if cv2.contourArea(contour) > 1000:
                    current_time = time.time()

                    if current_time - last_capture_time > 5:
                        attempt_count += 1
                        msg = (
                            f"🚨 MOTION DETECTED 🚨\n"
                            f"🕒 {time.ctime()}\n"
                            f"🔁 Count: {attempt_count}"
                        )
                        threading.Thread(
                            target=capture_and_alert,
                            kwargs=dict(
                                filename_prefix="intruder",
                                message=msg,
                                log_msg="Motion detected",
                                alarm=True,
                            ),
                            daemon=True,
                        ).start()

                        if current_time - last_video_time > 15:
                            threading.Thread(
                                target=lambda: send_video(record_video()), daemon=True
                            ).start()
                            last_video_time = current_time

                        last_capture_time = current_time

                    # Draw on local display only
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(
                        frame1,
                        "INTRUDER",
                        (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                    )

        elif status["system"] == "ON" and not can_motion_run():
            cv2.putText(
                frame1,
                "CAMERA BUSY",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2,
            )
        else:
            cv2.putText(
                frame1,
                "SYSTEM OFF",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )

        cv2.imshow("Security System", frame1)

        frame1 = frame2
        new_frame = camera.get_frame()
        if new_frame is None:
            time.sleep(0.05)
            continue
        frame2 = new_frame

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    camera.stop_capture()
    release_camera_api(PRIORITY_MOTION, "motion_detector")
    cv2.destroyAllWindows()

