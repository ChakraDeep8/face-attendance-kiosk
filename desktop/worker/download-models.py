"""Download the experimental InsightFace model pack into the worker bundle."""
from app.config import settings
import onnxruntime as ort
from insightface.app import FaceAnalysis

print(f"Preparing {settings.model_name} in {settings.model_root}")
available=ort.get_available_providers()
providers=[provider for provider in ("DmlExecutionProvider","CPUExecutionProvider") if provider in available]
model = FaceAnalysis(name=settings.model_name, root=str(settings.model_root), providers=providers)
model.prepare(ctx_id=-1, det_size=(640, 640))
print("Models are ready")
