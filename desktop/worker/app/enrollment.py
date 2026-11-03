from __future__ import annotations
from threading import Event, Thread, Lock
import base64, cv2, math, time, uuid, numpy as np
from .camera import WebcamCameraSource
from .database import repo
from .recognition import engine
from .schemas import CameraConfiguration
from .config import settings

POSES=["center","left","right"]

class EnrollmentSession:
    def __init__(self): self.thread=None; self.cancel_event=Event(); self.lock=Lock(); self.data={"running":False,"pose":"center","captured":0,"message":"Ready","complete":False,"error":None,"personId":None,"previewImage":None}
    def status(self):
        with self.lock: return dict(self.data)
    def start(self,name,employee_id,device_index,consent,person_id=None):
        if self.data["running"]: raise RuntimeError("Enrollment is already running")
        if not consent: raise ValueError("Biometric consent is required")
        self.cancel_event.clear(); self.data={"running":True,"pose":"center","captured":0,"message":"Look straight at the camera","complete":False,"error":None,"personId":None,"previewImage":None}
        self.thread=Thread(target=self._run,args=(name,employee_id,device_index,person_id),daemon=True); self.thread.start()
    def cancel(self): self.cancel_event.set()
    def _accept(self,pose,angles,first_turn_sign=None):
        pitch,yaw,roll=[float(v) for v in angles]
        if abs(roll)>25: return False
        if pose=="center": return abs(yaw)<16 and abs(pitch)<18
        if pose=="left": return abs(yaw)>12
        return first_turn_sign is not None and yaw*first_turn_sign < -12

    @staticmethod
    def _face_area(face):
        return max(0,face.bbox[2]-face.bbox[0])*max(0,face.bbox[3]-face.bbox[1])

    @classmethod
    def _primary_face(cls,faces):
        if not faces: return None,False
        ordered=sorted(faces,key=cls._face_area,reverse=True)
        crowded=len(ordered)>1 and cls._face_area(ordered[1])>=cls._face_area(ordered[0])*.60
        return ordered[0],crowded

    @classmethod
    def _guidance(cls,pose,faces,first_turn_sign=None):
        if not faces: return "No face detected — move closer and face the camera"
        face,crowded=cls._primary_face(faces)
        if crowded: return "Another foreground face is visible — only one person should be near the camera"
        pitch,yaw,roll=[float(v) for v in face.pose]
        if face.detection_score<.55: return "Face confidence is low — improve lighting"
        if face.quality<.12: return "Hold still — image is blurred"
        if abs(roll)>25: return "Keep your head upright"
        if pose=="center": return "Look straight at the camera and hold still"
        if pose=="left": return "Turn your head to one side and hold"
        if first_turn_sign is not None and yaw*first_turn_sign>=-12: return "Now turn to the opposite side and hold"
        return "Hold this position"
    def _run(self,name,employee_id,device_index,person_id=None):
        camera=WebcamCameraSource(CameraConfiguration(deviceIndex=device_index)); embeddings=[]; image_bytes=None; first_turn_sign=None
        try:
            engine.load(); camera.open()
            for index,pose in enumerate(POSES):
                with self.lock: self.data.update(pose=pose,message=f"Move your head {pose} slowly")
                deadline=time.time()+40; accepted=False; last_guidance="Position your face inside the guide"; qualifying_since=None
                frame_number=0
                while time.time()<deadline and not self.cancel_event.is_set():
                    frame=camera.read(); frame_number+=1
                    if frame_number%2==0:
                        preview=cv2.resize(frame,(640,360),interpolation=cv2.INTER_AREA)
                        _,jpeg=cv2.imencode(".jpg",preview,[cv2.IMWRITE_JPEG_QUALITY,72])
                        with self.lock: self.data["previewImage"]="data:image/jpeg;base64,"+base64.b64encode(jpeg).decode("ascii")
                    faces=engine.detect(frame)
                    face,crowded=self._primary_face(faces)
                    valid=face is not None and not crowded and face.detection_score>=.55 and face.quality>=.12 and self._accept(pose,face.pose,first_turn_sign)
                    if valid:
                        qualifying_since=qualifying_since or time.time()
                        remaining=max(0,math.ceil(2-(time.time()-qualifying_since)))
                        guidance=f"Hold still — capturing in {remaining}" if remaining else "Capturing now"
                    else:
                        qualifying_since=None
                        guidance=self._guidance(pose,faces,first_turn_sign)
                    last_guidance=guidance
                    with self.lock: self.data["message"]=guidance
                    if valid and time.time()-qualifying_since>=2:
                        if pose=="left":
                            yaw=float(face.pose[1]); first_turn_sign=1 if yaw>=0 else -1
                        embeddings.append(face.embedding.tolist()); accepted=True
                        if image_bytes is None: _,encoded=cv2.imencode(".jpg",frame); image_bytes=encoded.tobytes()
                        with self.lock: self.data.update(captured=index+1,message="Position captured")
                        time.sleep(.7); break
                    time.sleep(.15)
                if not accepted: raise RuntimeError(f"Could not capture {pose}: {last_guidance}")
            matrix=np.asarray(embeddings,dtype=np.float32); centroid=matrix.mean(axis=0); centroid/=np.linalg.norm(centroid) or 1; embeddings.append(centroid.tolist())
            duplicate=repo.find_duplicate(embeddings,exclude_person_id=person_id)
            if duplicate: raise RuntimeError(f"Face is already registered to {duplicate['name']} ({duplicate['employeeId']})")
            path=settings.data_root/"faces"/f"{uuid.uuid4().hex}.jpg"; path.write_bytes(image_bytes or b"")
            if person_id: repo.replace_biometrics(person_id,str(path),embeddings,settings.model_name)
            else: person_id=repo.save_person(name,employee_id,str(path),embeddings,settings.model_name)
            with self.lock: self.data.update(running=False,complete=True,personId=person_id,message="Enrollment complete")
        except Exception as exc:
            with self.lock: self.data.update(running=False,error=str(exc),message=str(exc))
        finally: camera.close()

enrollment=EnrollmentSession()
