import cv2
import threading
import time
import platform

class CameraThread:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._started = False
            return cls._instance

    def __init__(self):
        if self._started:
            return
        self._started = True
        self.cap = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self._running = False
        self._reader_thread = None

    def _open_camera(self, index):
        system = platform.system()

        if system == "Windows":
            return cv2.VideoCapture(index, cv2.CAP_DSHOW)
        elif system == "Darwin":  # macOS
            return cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        else:  # Linux
            return cv2.VideoCapture(index)

    def start_capture(self):
        if self._running:
            return
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._reader, daemon=True, name="cam_reader"
        )
        self._reader_thread.start()
        print("📷 Camera thread started")

    def stop_capture(self):
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        with self.frame_lock:
            self.latest_frame = None
        print("📷 Camera thread stopped")

    def _reader(self):
        while self._running:

            # 🔁 Try reconnect if camera not ready
            if self.cap is None or not self.cap.isOpened():
                for i in range(3):
                    c = self._open_camera(i)
                    if c.isOpened():
                        self.cap = c
                        print(f"✅ Camera connected at index {i}")
                        break
                else:
                    time.sleep(2)
                    continue

            ret, frame = self.cap.read()

            if ret:
                with self.frame_lock:
                    self.latest_frame = frame
            else:
                print("⚠️ Frame read failed, reconnecting...")
                self.cap.release()
                self.cap = None
                time.sleep(1)

            # 🔥 Prevent CPU overuse (important for macOS)
            time.sleep(0.01)

    def get_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def wait_for_frame(self, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            if self.get_frame() is not None:
                return True
            time.sleep(0.05)
        return False
    
    def stop_capture(self):
        self._running = False
        time.sleep(0.1)          # ← let reader thread finish current frame.read()
        if self.cap:
            self.cap.release()
            self.cap = None
        with self.frame_lock:
            self.latest_frame = None
        print("📷 Camera thread stopped")
    
    


camera = CameraThread()