import cv2
import asyncio
from aiortc import VideoStreamTrack
from av import VideoFrame

class CameraTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ret, frame = self.cap.read()
        if not ret:
            await asyncio.sleep(0.03)
            return await self.recv()

        frame = cv2.resize(frame, (640, 360))

        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame