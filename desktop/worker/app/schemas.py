from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class CameraSourceType(str, Enum):
    Webcam = "Webcam"
    Rtsp = "Rtsp"

class CameraConfiguration(BaseModel):
    sourceType: CameraSourceType = CameraSourceType.Webcam
    deviceIndex: int = 0
    rtspUrl: Optional[str] = None
    width: int = 1280
    height: int = 720
    recognitionFps: int = Field(5, ge=1, le=30)
    reconnectSeconds: int = Field(3, ge=1, le=60)

class MonitorStartRequest(BaseModel):
    camera: CameraConfiguration

class RegisterPersonRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    employeeId: str = Field(min_length=1, max_length=64)
    imageBase64: str
    embeddings: list[list[float]] = Field(min_length=1)
    consent: bool

class EncodeImageRequest(BaseModel):
    imageBase64: str

class RecognitionSettings(BaseModel):
    matchThreshold: float = Field(0.48, ge=0.2, le=0.9)
    attendanceCooldownMinutes: int = Field(10, ge=1, le=1440)
    alertCooldownSeconds: int = Field(15, ge=1, le=3600)
    snapshotRetentionDays: int = Field(30, ge=0, le=3650)
    modelName: str = "buffalo_s"
