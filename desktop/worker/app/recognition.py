from __future__ import annotations
from dataclasses import dataclass
from threading import Lock
import base64, cv2, gc, numpy as np
from .config import settings

@dataclass
class FaceSample:
    bbox: list[int]
    landmarks: list[list[float]]
    embedding: np.ndarray
    detection_score: float
    quality: float
    pose: list[float]

class RecognitionEngine:
    def __init__(self): self.app=None; self.error=None; self.provider=None; self.lock=Lock()
    @property
    def loaded(self): return self.app is not None
    def load(self,provider=None):
        requested=(provider or self.provider or "CPU").upper()
        if requested not in ("CPU","GPU"): raise ValueError("Processor must be CPU or GPU")
        with self.lock:
            if self.app is not None and self.provider==requested: return
            try:
                import onnxruntime as ort
                from insightface.app import FaceAnalysis
                available=ort.get_available_providers()
                if requested=="GPU":
                    if "DmlExecutionProvider" not in available: raise RuntimeError("DirectML GPU acceleration is not available on this computer")
                    providers=["DmlExecutionProvider","CPUExecutionProvider"]; ctx_id=0
                else:
                    providers=["CPUExecutionProvider"]; ctx_id=-1
                self.app=None; gc.collect()
                application=FaceAnalysis(name=settings.model_name,root=str(settings.model_root),providers=providers)
                application.prepare(ctx_id=ctx_id,det_size=(640,640))
                self.app=application; self.provider=requested; self.error=None
            except Exception as exc: self.error=str(exc); raise RuntimeError(f"Unable to load face model on {requested}: {exc}") from exc
    def detect(self, frame) -> list[FaceSample]:
        self.load(); faces=self.app.get(frame); result=[]
        for face in faces:
            box=[int(v) for v in face.bbox]; crop=frame[max(0,box[1]):max(0,box[3]),max(0,box[0]):max(0,box[2])]
            sharpness=float(cv2.Laplacian(crop,cv2.CV_64F).var()) if crop.size else 0
            embedding=np.asarray(face.normed_embedding,dtype=np.float32); embedding/=np.linalg.norm(embedding) or 1
            result.append(FaceSample(box,np.asarray(face.kps).tolist(),embedding,float(face.det_score),min(1.0,sharpness/250.0),np.asarray(getattr(face,"pose",[0,0,0]),dtype=float).tolist()))
        return result
    def decode(self, value):
        payload=value.split(",",1)[-1]; data=np.frombuffer(base64.b64decode(payload),np.uint8); image=cv2.imdecode(data,cv2.IMREAD_COLOR)
        if image is None: raise ValueError("Image could not be decoded")
        return image
    def validate_image(self, value):
        image=self.decode(value); faces=self.detect(image)
        if len(faces)!=1: return False,f"Expected exactly one face; found {len(faces)}",faces
        face=faces[0]; width=face.bbox[2]-face.bbox[0]; height=face.bbox[3]-face.bbox[1]
        if min(width,height)<120: return False,"Face is too small; use a closer image",faces
        if face.detection_score<.75: return False,"Face detection confidence is too low",faces
        if face.quality<.25: return False,"Image is too blurred for registration",faces
        return True,"Face image is suitable",faces

engine=RecognitionEngine()
