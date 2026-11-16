from __future__ import annotations
import argparse, asyncio, base64, json, uuid, cv2, numpy as np
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from .config import settings
from .database import repo
from .monitor import monitor
from .recognition import engine
from .enrollment import enrollment
from .schemas import EncodeImageRequest, MonitorStartRequest, RegisterPersonRequest, RecognitionSettings

app=FastAPI(title="Verity Recognition Worker",docs_url=None,redoc_url=None)

def authorize(x_verity_token: str = Header(default="")):
    if x_verity_token!=settings.token: raise HTTPException(401,"Invalid worker token")

@app.get("/health",dependencies=[Depends(authorize)])
def health(): return {"status":"ok","modelLoaded":engine.loaded,"databaseReady":repo.path.exists(),"version":"0.1.0","time":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}

@app.post("/models/load",dependencies=[Depends(authorize)])
def load_models(provider: str="CPU"):
    if monitor.running or enrollment.status()["running"]: raise HTTPException(409,"Stop monitoring or enrollment before changing processor")
    engine.load(provider); return {"loaded":True,"model":settings.model_name,"provider":engine.provider}

@app.post("/faces/encode-image",dependencies=[Depends(authorize)])
@app.post("/faces/validate-registration",dependencies=[Depends(authorize)])
def encode_image(request: EncodeImageRequest):
    valid,message,faces=engine.validate_image(request.imageBase64)
    return {"valid":valid,"message":message,"faceCount":len(faces),"quality":faces[0].quality if len(faces)==1 else 0,"embedding":faces[0].embedding.tolist() if valid else []}

@app.get("/people",dependencies=[Depends(authorize)])
def people():
    result=repo.people()
    for person in result:
        path=repo.person_image_path(person["id"])
        image=cv2.imread(path) if path else None
        if image is None: person["imageData"]=None; continue
        height,width=image.shape[:2]; scale=min(160/width,160/height,1); thumb=cv2.resize(image,(max(1,int(width*scale)),max(1,int(height*scale))),interpolation=cv2.INTER_AREA)
        _,jpeg=cv2.imencode(".jpg",thumb,[cv2.IMWRITE_JPEG_QUALITY,75])
        person["imageData"]="data:image/jpeg;base64,"+base64.b64encode(jpeg).decode("ascii")
    return result

@app.post("/people",dependencies=[Depends(authorize)])
def register(request: RegisterPersonRequest):
    if not request.consent: raise HTTPException(400,"Biometric consent is required")
    valid,message,_=engine.validate_image(request.imageBase64)
    if not valid: raise HTTPException(400,message)
    duplicate=repo.find_duplicate(request.embeddings)
    if duplicate: raise HTTPException(409,f"Face is already registered to {duplicate['name']} ({duplicate['employeeId']})")
    raw=base64.b64decode(request.imageBase64.split(",",1)[-1]); path=settings.data_root/"faces"/f"{uuid.uuid4().hex}.jpg"; path.write_bytes(raw)
    try: person_id=repo.save_person(request.name.strip(),request.employeeId.strip(),str(path),request.embeddings,settings.model_name)
    except Exception as exc:
        if "UNIQUE" in str(exc): raise HTTPException(409,"Employee ID already exists")
        raise
    return {"id":person_id}

@app.delete("/people/{person_id}",status_code=204,dependencies=[Depends(authorize)])
def delete_person(person_id: str): repo.delete_person(person_id)

@app.patch("/people/{person_id}",dependencies=[Depends(authorize)])
def update_person(person_id: str, payload: dict):
    try: repo.update_person(person_id,payload.get("name","").strip(),payload.get("employeeId","").strip())
    except Exception as exc:
        if "UNIQUE" in str(exc): raise HTTPException(409,"Employee ID already exists")
        raise HTTPException(400,str(exc))
    return {"updated":True}

@app.put("/people/{person_id}/face",dependencies=[Depends(authorize)])
def replace_person_face(person_id: str, request: RegisterPersonRequest):
    valid,message,_=engine.validate_image(request.imageBase64)
    if not valid: raise HTTPException(400,message)
    duplicate=repo.find_duplicate(request.embeddings,exclude_person_id=person_id)
    if duplicate: raise HTTPException(409,f"Face is already registered to {duplicate['name']} ({duplicate['employeeId']})")
    raw=base64.b64decode(request.imageBase64.split(",",1)[-1]); path=settings.data_root/"faces"/f"{uuid.uuid4().hex}.jpg"; path.write_bytes(raw)
    try:
        repo.update_person(person_id,request.name.strip(),request.employeeId.strip())
        repo.replace_biometrics(person_id,str(path),request.embeddings,settings.model_name)
    except Exception:
        path.unlink(missing_ok=True); raise
    return {"updated":True}

@app.post("/enrollment/start",dependencies=[Depends(authorize)])
def enrollment_start(payload: dict): enrollment.start(payload.get("name","").strip(),payload.get("employeeId","").strip(),int(payload.get("deviceIndex",0)),bool(payload.get("consent")),payload.get("personId")); return enrollment.status()

@app.get("/enrollment/status",dependencies=[Depends(authorize)])
def enrollment_status(): return enrollment.status()

@app.post("/enrollment/cancel",dependencies=[Depends(authorize)])
def enrollment_cancel(): enrollment.cancel(); return enrollment.status()

@app.get("/events",dependencies=[Depends(authorize)])
def events(limit: int=100):
    result=repo.events(min(max(limit,1),1000))
    for event in result:
        path=event.get("snapshotPath"); event["imageData"]=None
        if not path or not Path(path).exists(): continue
        image=cv2.imread(path)
        if image is None: continue
        height,width=image.shape[:2]; scale=min(240/width,160/height,1); thumb=cv2.resize(image,(max(1,int(width*scale)),max(1,int(height*scale))),interpolation=cv2.INTER_AREA)
        _,jpeg=cv2.imencode(".jpg",thumb,[cv2.IMWRITE_JPEG_QUALITY,75]); event["imageData"]="data:image/jpeg;base64,"+base64.b64encode(jpeg).decode("ascii")
    return result

@app.delete("/events/{event_id}",status_code=204,dependencies=[Depends(authorize)])
def delete_event(event_id: str):
    if not repo.delete_event(event_id): raise HTTPException(404,"Event not found")

@app.get("/monitor/calibration",dependencies=[Depends(authorize)])
def get_calibration():
    values=repo.settings(); return {"zone":values["detectionZone"],"line":values["crossingLine"]}

@app.put("/monitor/calibration",dependencies=[Depends(authorize)])
def set_calibration(payload: dict):
    zone=payload.get("zone"); line=payload.get("line")
    if not zone or not line: raise HTTPException(400,"Both face zone and crossing line are required")
    required=("x1","y1","x2","y2")
    try: values=[float(item[key]) for item in (zone,line) for key in required]
    except (KeyError,TypeError,ValueError): raise HTTPException(400,"Calibration coordinates are invalid")
    if any(value<0 or value>1 for value in values): raise HTTPException(400,"Calibration coordinates must be between 0 and 1")
    if abs(float(zone["x2"])-float(zone["x1"]))<.02 or abs(float(zone["y2"])-float(zone["y1"]))<.02: raise HTTPException(400,"Face detection zone is too small")
    if np.hypot(float(line["x2"])-float(line["x1"]),float(line["y2"])-float(line["y1"]))<.02: raise HTTPException(400,"Crossing line is too short")
    repo.set_calibration(zone,line); return {"zone":zone,"line":line}

@app.post("/monitor/start",dependencies=[Depends(authorize)])
def monitor_start(request: MonitorStartRequest): monitor.start(request.camera); return monitor.status()

@app.post("/monitor/stop",dependencies=[Depends(authorize)])
def monitor_stop(): monitor.stop(); return monitor.status()

@app.get("/monitor/status",dependencies=[Depends(authorize)])
def monitor_status(): return monitor.status()

@app.websocket("/monitor/events")
async def monitor_events(websocket: WebSocket):
    if websocket.headers.get("x-verity-token")!=settings.token: await websocket.close(code=4401); return
    await websocket.accept(); queue=monitor.subscribe()
    try:
        while True:
            try: event=await asyncio.to_thread(queue.get,True,1); await websocket.send_json(event)
            except __import__("queue").Empty: await websocket.send_json({"type":"heartbeat"})
    except WebSocketDisconnect: pass
    finally: monitor.unsubscribe(queue)

def run():
    parser=argparse.ArgumentParser(); parser.add_argument("--port",type=int,default=8792); args=parser.parse_args()
    import uvicorn; uvicorn.run(app,host="127.0.0.1",port=args.port,log_level="warning")

if __name__=="__main__": run()
