from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
import os, shutil, subprocess, sys, time, cv2, numpy as np
from .schemas import CameraConfiguration, CameraSourceType

class CameraSource(ABC):
    def __init__(self, config: CameraConfiguration): self.config=config; self.capture=None; self.error=None
    @abstractmethod
    def _target(self): ...
    def open(self):
        if self.config.sourceType==CameraSourceType.Rtsp:
            # TCP avoids the macro-block corruption commonly seen when RTSP video packets are lost over UDP.
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]="rtsp_transport;tcp|stimeout;8000000|rw_timeout;8000000|max_delay;500000"
            params=[]
            if hasattr(cv2,"CAP_PROP_OPEN_TIMEOUT_MSEC"): params += [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,8000]
            if hasattr(cv2,"CAP_PROP_READ_TIMEOUT_MSEC"): params += [cv2.CAP_PROP_READ_TIMEOUT_MSEC,8000]
            self.capture=cv2.VideoCapture(self._target(),cv2.CAP_FFMPEG,params)
            if not self.capture.isOpened():
                self.close()
                raise RuntimeError("Unable to open the RTSP stream. Check its URL, credentials, and network connection.")
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE,1)
            ok,frame=self.capture.read()
            if not ok or frame is None or frame.size==0:
                self.close()
                raise RuntimeError("RTSP connected but did not produce a decodable video frame.")
        else:
            attempted=[]
            # Some Windows cameras fail through Media Foundation but work through DirectShow.
            for name,backend in (("DirectShow",cv2.CAP_DSHOW),("Media Foundation",cv2.CAP_MSMF),("Automatic",cv2.CAP_ANY)):
                attempted.append(name)
                capture=cv2.VideoCapture(self._target(),backend)
                if capture.isOpened():
                    ok,_=capture.read()
                    if ok:
                        self.capture=capture
                        self.error=None
                        break
                capture.release()
            if self.capture is None:
                raise RuntimeError(
                    f"Unable to open webcam {self.config.deviceIndex}. Close other camera apps, check Windows camera permission, "
                    f"or select another device. Tried: {', '.join(attempted)}."
                )
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH,self.config.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT,self.config.height)
    def read(self):
        if self.capture is None or not self.capture.isOpened(): self.open()
        ok,frame=self.capture.read()
        if not ok: self.close(); time.sleep(self.config.reconnectSeconds); raise RuntimeError("Camera frame unavailable; reconnecting")
        return frame
    def close(self):
        if self.capture is not None: self.capture.release(); self.capture=None

class WebcamCameraSource(CameraSource):
    def _target(self): return self.config.deviceIndex

class RtspCameraSource(CameraSource):
    def __init__(self,config):
        super().__init__(config); self.last_signature=None; self.process=None; self.frames=Queue(maxsize=2); self.reader=None; self.reader_stop=Event(); self.pending_frame=None

    def _target(self):
        if not self.config.rtspUrl: raise ValueError("RTSP URL is required")
        return self.config.rtspUrl

    @staticmethod
    def _integrity(frame):
        sample=cv2.cvtColor(cv2.resize(frame,(320,240),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY).astype(np.float32)
        dx=np.abs(np.diff(sample,axis=1)); dy=np.abs(np.diff(sample,axis=0))
        boundary=(float(np.mean(dx[:,15::16]))+float(np.mean(dy[15::16,:])))/2
        interior=(float(np.mean(dx))+float(np.mean(dy)))/2
        signature=cv2.resize(sample,(160,120),interpolation=cv2.INTER_AREA).astype(np.uint8)
        return signature,boundary/(interior+1e-3)

    def _ffmpeg_path(self):
        bundle=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[1]))
        for candidate in (bundle/"ffmpeg.exe",bundle/"bin"/"ffmpeg.exe"):
            if candidate.exists(): return str(candidate)
        return shutil.which("ffmpeg")

    def _reader_loop(self):
        width,height=960,720; frame_bytes=width*height*3
        try:
            while not self.reader_stop.is_set() and self.process and self.process.poll() is None:
                payload=bytearray()
                while len(payload)<frame_bytes and not self.reader_stop.is_set():
                    chunk=self.process.stdout.read(frame_bytes-len(payload))
                    if not chunk: break
                    payload.extend(chunk)
                if len(payload)!=frame_bytes: break
                frame=np.frombuffer(payload,dtype=np.uint8).reshape((height,width,3)).copy()
                try: self.frames.put_nowait(frame)
                except Full:
                    try: self.frames.get_nowait()
                    except Empty: pass
                    try: self.frames.put_nowait(frame)
                    except Full: pass
        except Exception as exc: self.error=str(exc)

    def open(self):
        self.close(); ffmpeg=self._ffmpeg_path()
        if not ffmpeg:
            super().open(); self.last_signature=None; return
        self.frames=Queue(maxsize=2); self.reader_stop.clear(); fps=max(5,min(15,self.config.recognitionFps*2))
        video_filter=f"fps={fps},scale=960:720:force_original_aspect_ratio=decrease,pad=960:720:(ow-iw)/2:(oh-ih)/2"
        command=[ffmpeg,"-hide_banner","-loglevel","error","-rtsp_transport","tcp","-fflags","+discardcorrupt","-flags","low_delay","-i",self._target(),"-an","-sn","-dn","-vf",video_filter,"-pix_fmt","bgr24","-f","rawvideo","pipe:1"]
        self.process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.reader=Thread(target=self._reader_loop,daemon=True,name="verity-ffmpeg-reader"); self.reader.start()
        try: self.pending_frame=self.frames.get(timeout=10)
        except Empty:
            self.close(); raise RuntimeError("RTSP connected but FFmpeg did not produce a clean frame within 10 seconds")
        self.last_signature=None

    def read(self):
        if self.pending_frame is not None: frame=self.pending_frame; self.pending_frame=None
        elif self.process is not None:
            try: frame=self.frames.get(timeout=8)
            except Empty:
                self.close(); time.sleep(self.config.reconnectSeconds); raise RuntimeError("RTSP frame timeout; reconnecting")
            while True:
                try: frame=self.frames.get_nowait()
                except Empty: break
        else: frame=super().read()
        signature,block_ratio=self._integrity(frame)
        temporal=0 if self.last_signature is None else float(np.mean(cv2.absdiff(signature,self.last_signature)))
        self.last_signature=signature
        if block_ratio>1.28 or temporal>45:
            self.close(); self.last_signature=None
            time.sleep(self.config.reconnectSeconds)
            raise RuntimeError("Corrupted RTSP frame discarded; reconnecting for a clean keyframe")
        return frame

    def close(self):
        self.reader_stop.set()
        if self.process is not None:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill()
            self.process=None
        if self.reader and self.reader.is_alive(): self.reader.join(timeout=2)
        self.reader=None; self.pending_frame=None; super().close(); self.last_signature=None

def create_camera(config): return WebcamCameraSource(config) if config.sourceType==CameraSourceType.Webcam else RtspCameraSource(config)
