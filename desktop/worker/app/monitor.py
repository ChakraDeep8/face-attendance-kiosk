from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread
import base64, cv2, numpy as np, time
from .camera import create_camera
from .config import settings
from .database import repo
from .recognition import engine

class Monitor:
    def __init__(self):
        self.thread=None; self.stop_event=Event(); self.running=False; self.state="stopped"; self.error=None; self.fps=0.0; self.camera_name=""; self.preview_image=None; self.subscribers=[]; self.lock=Lock()
    def start(self, config):
        if self.running: raise RuntimeError("Monitor is already running")
        self.stop_event.clear(); self.thread=Thread(target=self._run,args=(config,),daemon=True,name="verity-monitor"); self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.thread: self.thread.join(timeout=5)
        self.running=False; self.state="stopped"
    def subscribe(self):
        queue=Queue(maxsize=20)
        with self.lock: self.subscribers.append(queue)
        return queue
    def unsubscribe(self, queue):
        with self.lock:
            if queue in self.subscribers: self.subscribers.remove(queue)
    def publish(self, event):
        with self.lock:
            for queue in self.subscribers:
                if not queue.full(): queue.put_nowait(event)
    def status(self):
        with self.lock: preview=self.preview_image
        return {"running":self.running,"state":self.state,"camera":self.camera_name,"fps":self.fps,"error":self.error,"previewImage":preview}
    def _match(self, embedding):
        index=repo.template_index()
        if not index: return None,"Unknown",0.0
        scores=[(float(np.dot(embedding,vector)),person_id,name) for person_id,name,_,vector in index]
        score,person_id,name=max(scores,key=lambda x:x[0]); threshold=float(repo.settings()["matchThreshold"])
        return (person_id,name,score) if score>=threshold else (None,"Unknown",score)
    def _snapshot(self, frame):
        path=settings.data_root/"alerts"/f"unknown-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}.jpg"; cv2.imwrite(str(path),frame); return str(path)
    def _run(self, config):
        camera=create_camera(config); self.running=True; self.state="starting"; self.camera_name="Webcam" if config.sourceType.value=="Webcam" else "RTSP"
        interval=1/max(1,config.recognitionFps); last_frame=time.perf_counter(); frames=0; clock=time.perf_counter()
        try:
            engine.load(); camera.open(); self.state="running"; repo.purge_snapshots(int(repo.settings()["snapshotRetentionDays"]))
            while not self.stop_event.is_set():
                began=time.perf_counter()
                try: frame=camera.read()
                except Exception as exc: self.error=str(exc); self.state="reconnecting"; continue
                self.state="running"; self.error=None; frames+=1
                if time.perf_counter()-clock>=2: self.fps=frames/(time.perf_counter()-clock); frames=0; clock=time.perf_counter()
                faces=engine.detect(frame)
                preview=frame.copy()
                for face in faces:
                    person_id,name,score=self._match(face.embedding); config_values=repo.settings()
                    x1,y1,x2,y2=face.bbox; color=(70,220,120) if person_id else (40,50,235)
                    cv2.rectangle(preview,(x1,y1),(x2,y2),color,3)
                    cv2.putText(preview,name if person_id else "Unknown",(x1,max(24,y1-10)),cv2.FONT_HERSHEY_SIMPLEX,.75,color,2,cv2.LINE_AA)
                    if person_id:
                        cooldown=int(config_values["attendanceCooldownMinutes"])*60
                        if repo.recent_event(person_id,"Authorized",cooldown): continue
                        event=repo.add_event("Authorized",person_id,name,round(score*100,2),self.camera_name)
                    else:
                        cooldown=int(config_values["alertCooldownSeconds"])
                        if repo.recent_event(None,"Unknown",cooldown): continue
                        event=repo.add_event("Unknown",None,"Unknown person",round(score*100,2),self.camera_name,self._snapshot(frame))
                    self.publish(event)
                display=cv2.resize(preview,(800,450),interpolation=cv2.INTER_AREA)
                _,jpeg=cv2.imencode(".jpg",display,[cv2.IMWRITE_JPEG_QUALITY,72])
                with self.lock: self.preview_image="data:image/jpeg;base64,"+base64.b64encode(jpeg).decode("ascii")
                elapsed=time.perf_counter()-began
                if elapsed<interval: self.stop_event.wait(interval-elapsed)
        except Exception as exc: self.error=str(exc); self.state="failed"
        finally:
            camera.close(); self.running=False
            with self.lock: self.preview_image=None

monitor=Monitor()
