from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json, sqlite3, uuid
import numpy as np
from .config import settings

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS people(id TEXT PRIMARY KEY,name TEXT NOT NULL,employee_id TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,consent_at TEXT NOT NULL,image_path TEXT);
CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY,person_id TEXT NOT NULL,embedding BLOB NOT NULL,pose TEXT NOT NULL,model_version TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,result TEXT NOT NULL,person_id TEXT,display_name TEXT NOT NULL,confidence REAL NOT NULL,timestamp TEXT NOT NULL,camera TEXT NOT NULL,snapshot_path TEXT,FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,action TEXT NOT NULL,detail TEXT NOT NULL,timestamp TEXT NOT NULL);
"""

class Repository:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.data_root / "verity.db"
        with self.connect() as db: db.executescript(SCHEMA)
        self._defaults()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20, check_same_thread=False)
        db.row_factory = sqlite3.Row
        try: yield db; db.commit()
        finally: db.close()

    def _defaults(self):
        defaults = {"matchThreshold": .48,"attendanceCooldownMinutes": 10,"alertCooldownSeconds": 15,"snapshotRetentionDays": 30,"modelName": settings.model_name,
                    "detectionZone":{"x1":.291,"y1":.556,"x2":.628,"y2":.864},
                    "crossingLine":{"x1":.240,"y1":.927,"x2":.631,"y2":.925}}
        with self.connect() as db:
            for key, value in defaults.items(): db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(key,json.dumps(value)))

    def settings(self):
        with self.connect() as db: return {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT key,value FROM settings")}

    def set_calibration(self, zone, line):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('detectionZone',?)",(json.dumps(zone),))
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('crossingLine',?)",(json.dumps(line),))
            self._audit(db,"monitor.calibration",json.dumps({"zone":zone,"line":line}))

    def save_person(self, name, employee_id, image_path, embeddings, model="buffalo_s"):
        now = datetime.now(timezone.utc).isoformat(); person_id = str(uuid.uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO people VALUES(?,?,?,?,1,?,?)",(person_id,name,employee_id,now,now,image_path))
            for index, embedding in enumerate(embeddings):
                vector = np.asarray(embedding,dtype=np.float32); vector /= np.linalg.norm(vector) or 1
                db.execute("INSERT INTO templates VALUES(?,?,?,?,?,?)",(str(uuid.uuid4()),person_id,vector.tobytes(),f"pose-{index}",model,now))
            self._audit(db,"person.registered",f"{name} ({employee_id})")
        return person_id

    def people(self):
        with self.connect() as db:
            rows=db.execute("SELECT p.*,COUNT(t.id) templates FROM people p LEFT JOIN templates t ON t.person_id=p.id GROUP BY p.id ORDER BY p.created_at DESC").fetchall()
            return [{"id":r["id"],"name":r["name"],"employeeId":r["employee_id"],"createdAt":r["created_at"],"templateCount":r["templates"],"active":bool(r["active"])} for r in rows]

    def person_image_path(self, person_id):
        with self.connect() as db:
            row=db.execute("SELECT image_path FROM people WHERE id=?",(person_id,)).fetchone()
            return row["image_path"] if row else None

    def template_index(self):
        with self.connect() as db:
            rows=db.execute("SELECT t.person_id,t.embedding,p.name,p.employee_id FROM templates t JOIN people p ON p.id=t.person_id WHERE p.active=1").fetchall()
            return [(r["person_id"],r["name"],r["employee_id"],np.frombuffer(r["embedding"],dtype=np.float32)) for r in rows]

    def find_duplicate(self, embeddings, threshold=.72, exclude_person_id=None):
        index = self.template_index()
        if not index: return None
        candidates = []
        for embedding in embeddings:
            vector=np.asarray(embedding,dtype=np.float32); vector/=np.linalg.norm(vector) or 1
            for person_id,name,employee_id,known in index:
                if person_id == exclude_person_id: continue
                candidates.append((float(np.dot(vector,known)),person_id,name,employee_id))
        if not candidates: return None
        score,person_id,name,employee_id=max(candidates,key=lambda item:item[0])
        return {"score":score,"personId":person_id,"name":name,"employeeId":employee_id} if score>=threshold else None

    def recent_event(self, person_id, result, seconds):
        cutoff=(datetime.now(timezone.utc)-timedelta(seconds=seconds)).isoformat()
        with self.connect() as db: return db.execute("SELECT 1 FROM events WHERE person_id IS ? AND result=? AND timestamp>=? LIMIT 1",(person_id,result,cutoff)).fetchone() is not None

    def add_event(self, result, person_id, display_name, confidence, camera, snapshot_path=None):
        event={"id":str(uuid.uuid4()),"result":result,"personId":person_id,"displayName":display_name,"confidence":confidence,"timestamp":datetime.now(timezone.utc).isoformat(),"camera":camera,"snapshotPath":snapshot_path}
        with self.connect() as db:
            db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",(event["id"],result,person_id,display_name,confidence,event["timestamp"],camera,snapshot_path)); self._audit(db,"recognition.event",f"{result}: {display_name}")
        return event

    def events(self, limit=100):
        with self.connect() as db:
            rows=db.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",(limit,)).fetchall()
            return [{"id":r["id"],"result":r["result"],"personId":r["person_id"],"displayName":r["display_name"],"confidence":r["confidence"],"timestamp":r["timestamp"],"camera":r["camera"],"snapshotPath":r["snapshot_path"]} for r in rows]

    def delete_event(self, event_id):
        with self.connect() as db:
            row=db.execute("SELECT snapshot_path,display_name FROM events WHERE id=?",(event_id,)).fetchone()
            if not row: return False
            db.execute("DELETE FROM events WHERE id=?",(event_id,)); self._audit(db,"recognition.event.deleted",f"{event_id}: {row['display_name']}")
        if row["snapshot_path"]: Path(row["snapshot_path"]).unlink(missing_ok=True)
        return True

    def delete_person(self, person_id):
        with self.connect() as db:
            row=db.execute("SELECT image_path FROM people WHERE id=?",(person_id,)).fetchone()
            db.execute("DELETE FROM people WHERE id=?",(person_id,)); self._audit(db,"person.deleted",person_id)
        if row and row["image_path"]: Path(row["image_path"]).unlink(missing_ok=True)

    def update_person(self, person_id, name, employee_id):
        with self.connect() as db:
            db.execute("UPDATE people SET name=?,employee_id=? WHERE id=?",(name,employee_id,person_id))
            if db.total_changes == 0: raise ValueError("Person not found")
            self._audit(db,"person.updated",f"{name} ({employee_id})")

    def replace_biometrics(self, person_id, image_path, embeddings, model="buffalo_s"):
        now=datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            row=db.execute("SELECT image_path,name,employee_id FROM people WHERE id=?",(person_id,)).fetchone()
            if not row: raise ValueError("Person not found")
            old_path=row["image_path"]
            db.execute("DELETE FROM templates WHERE person_id=?",(person_id,))
            for index,embedding in enumerate(embeddings):
                vector=np.asarray(embedding,dtype=np.float32); vector/=np.linalg.norm(vector) or 1
                db.execute("INSERT INTO templates VALUES(?,?,?,?,?,?)",(str(uuid.uuid4()),person_id,vector.tobytes(),f"pose-{index}",model,now))
            db.execute("UPDATE people SET image_path=? WHERE id=?",(image_path,person_id))
            self._audit(db,"person.face-retaken",f"{row['name']} ({row['employee_id']})")
        if old_path and old_path != image_path: Path(old_path).unlink(missing_ok=True)

    def purge_snapshots(self, days):
        cutoff=datetime.now(timezone.utc)-timedelta(days=days)
        for path in (settings.data_root/"alerts").glob("*.jpg"):
            if datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)<cutoff: path.unlink(missing_ok=True)

    @staticmethod
    def _audit(db, action, detail): db.execute("INSERT INTO audit VALUES(?,?,?,?)",(str(uuid.uuid4()),action,detail,datetime.now(timezone.utc).isoformat()))

repo = Repository()
