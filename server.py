import os
import sys
import cv2
import time
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, PlainTextResponse
from typing import List

from fastapi import Request
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer
from webrtc import CameraTrack

app = FastAPI()

# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
VIDEO_FOLDER = os.path.join(BASE_DIR, "videos")
LOG_FILE = os.path.join(BASE_DIR, "logs", "activity.txt")

PRIORITY_MOTION = 1
PRIORITY_STREAM = 2
PRIORITY_AUTH = 3

# ================= GLOBAL STATE =================

status = {"system": "OFF"}

camera_lock = threading.Lock()
current_priority = 0
current_user = None
last_heartbeat = 0
LEASE_TIMEOUT = 10

latest_frame = None
camera_running = False

clients: List[WebSocket] = []

media_cache = {"images": [], "videos": []}
last_media_scan = 0

# ================= CAMERA THREAD =================


def camera_loop():
    global latest_frame, camera_running

    cap = cv2.VideoCapture(0)
    camera_running = True

    while camera_running:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.resize(frame, (640, 360))  # 🔥 reduce load
        latest_frame = frame

        time.sleep(0.03)  # ~30 FPS → ~10–15 FPS

    cap.release()


def start_camera():
    global camera_running
    if not camera_running:
        threading.Thread(target=camera_loop, daemon=True).start()


def stop_camera():
    global camera_running
    camera_running = False


# ================= PRIORITY =================


def acquire_priority(priority, name):
    global current_priority, current_user, last_heartbeat

    with camera_lock:
        now = time.time()

        if current_priority != 0 and (now - last_heartbeat > LEASE_TIMEOUT):
            current_priority = 0
            current_user = None

        if priority >= current_priority:
            current_priority = priority
            current_user = name
            last_heartbeat = now
            start_camera()
            return True

        return False


def release_priority(priority, name):
    global current_priority, current_user

    with camera_lock:
        if current_user == name and current_priority == priority:
            current_priority = 0
            current_user = None
            stop_camera()


# ================= WEBSOCKET =================


async def broadcast(data):
    dead = []
    for ws in clients:
        try:
            await ws.send_json(data)
        except:
            dead.append(ws)

    for d in dead:
        clients.remove(d)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in clients:
            clients.remove(ws)


# ================= STREAM =================


def frame_generator():
    name = "stream"
    acquire_priority(PRIORITY_STREAM, name)

    try:
        while True:
            if latest_frame is None:
                time.sleep(0.05)
                continue

            _, buffer = cv2.imencode(
                ".jpg", latest_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            )

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )

            time.sleep(0.03)

    finally:
        release_priority(PRIORITY_STREAM, name)


pcs = set()
audio_player = None


def _default_audio_format():
    if sys.platform == "darwin":
        return "avfoundation"
    if sys.platform.startswith("win"):
        return "dshow"
    return "alsa"


def get_audio_track():
    global audio_player

    if audio_player is None:
        source = os.getenv("AUDIO_SOURCE", "default")
        fmt = os.getenv("AUDIO_FORMAT", _default_audio_format())
        options = {}
        device = os.getenv("AUDIO_DEVICE")
        if device:
            options["audio"] = device

        try:
            audio_player = MediaPlayer(source, format=fmt, options=options or None)
        except Exception:
            audio_player = None

    if audio_player and audio_player.audio:
        return audio_player.audio
    return None

@app.post("/offer")
async def offer(request: Request):
    params = await request.json()

    config = RTCConfiguration(
        iceServers=[
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
            RTCIceServer(
                urls="turn:openrelay.metered.ca:80",
                username="openrelayproject",
                credential="openrelayproject",
            ),
            RTCIceServer(
                urls="turn:openrelay.metered.ca:443?transport=tcp",
                username="openrelayproject",
                credential="openrelayproject",
            ),
            RTCIceServer(
                urls="turns:openrelay.metered.ca:443?transport=tcp",
                username="openrelayproject",
                credential="openrelayproject",
            ),
        ]
    )

    pc = RTCPeerConnection(configuration=config)
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_state_change():
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)

    # attach camera
    pc.addTrack(CameraTrack())

    # attach microphone audio if available
    audio_track = get_audio_track()
    if audio_track:
        pc.addTrack(audio_track)

    # handle SDP
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}





@app.get("/", response_class=HTMLResponse)
async def home():
    with open(os.path.join(BASE_DIR, "dashboard.html"), "r") as f:
        return f.read()


@app.get("/video")
def video():
    return StreamingResponse(
        frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ================= STATUS =================


@app.get("/status")
async def get_status():
    return {
        "system": status["system"],
        "camera_running": camera_running,
        "current_user": current_user,
        "current_priority": current_priority,
    }


@app.get("/camera/priority")
async def get_camera_priority():
    return {
        "camera_running": camera_running,
        "current_user": current_user,
        "current_priority": current_priority,
    }


@app.get("/on")
async def turn_on():
    status["system"] = "ON"
    await broadcast({"type": "status", "data": status})
    return {"ok": True}


@app.get("/off")
async def turn_off():
    status["system"] = "OFF"
    await broadcast({"type": "status", "data": status})
    return {"ok": True}


# ================= MEDIA =================


def refresh_media():
    global last_media_scan

    if time.time() - last_media_scan > 5:
        media_cache["images"] = sorted(os.listdir(IMAGE_FOLDER), reverse=True)
        media_cache["videos"] = sorted(os.listdir(VIDEO_FOLDER), reverse=True)
        last_media_scan = time.time()


@app.get("/api/images")
async def get_images():
    refresh_media()
    return media_cache["images"]


@app.get("/api/videos")
async def get_videos():
    refresh_media()
    return media_cache["videos"]


@app.get("/image/{name}")
def get_image(name: str):
    return FileResponse(os.path.join(IMAGE_FOLDER, name))


@app.get("/video_file/{name}")
def get_video(name: str):
    return FileResponse(os.path.join(VIDEO_FOLDER, name))


# ================= LOGS =================


def tail_log(n=50):
    if not os.path.exists(LOG_FILE):
        return "No logs"

    with open(LOG_FILE, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(size - 5000, 0))
        return f.read().decode(errors="ignore")


@app.get("/logs", response_class=PlainTextResponse)
async def logs():
    return tail_log()


# ================= EVENT LOOP =================


async def push_updates():
    while True:
        await broadcast(
            {
                "type": "heartbeat",
                "data": {
                    "camera_running": camera_running,
                    "current_user": current_user,
                    "priority": current_priority,
                },
            }
        )
        await asyncio.sleep(3)


@app.on_event("startup")
async def startup():
    asyncio.create_task(push_updates())
