import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Camera,
  Check,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileImage,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Trash2,
  Upload,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import "./styles.css";
import { api, type ApiEvent, type ApiPerson } from "./api";
import {
  describeEnrollment,
  describeLiveBurst,
  prepareFaceEngine,
} from "./face";

type Person = {
  id: string;
  name: string;
  employeeId: string;
  initials: string;
  accent: string;
  created: string;
  status: "Active" | "Archived";
};
type Event = {
  id: string;
  person: string;
  employeeId: string;
  time: string;
  result: "Verified" | "Rejected" | "Duplicate";
  confidence: number;
  device: string;
};
const demoPeople: Person[] = [
  {
    id: "1",
    name: "Anika Rao",
    employeeId: "EST-0241",
    initials: "AR",
    accent: "#d99f85",
    created: "Oct 28, 2026",
    status: "Active",
  },
  {
    id: "2",
    name: "Rohan Mehta",
    employeeId: "EST-0187",
    initials: "RM",
    accent: "#8bb5a2",
    created: "Oct 27, 2026",
    status: "Active",
  },
  {
    id: "3",
    name: "Maya Shah",
    employeeId: "EST-0312",
    initials: "MS",
    accent: "#9b91c5",
    created: "Oct 24, 2026",
    status: "Active",
  },
];
const demoEvents: Event[] = [
  {
    id: "1",
    person: "Anika Rao",
    employeeId: "EST-0241",
    time: "09:04:22",
    result: "Verified",
    confidence: 98,
    device: "Front desk kiosk",
  },
  {
    id: "2",
    person: "Rohan Mehta",
    employeeId: "EST-0187",
    time: "08:57:10",
    result: "Verified",
    confidence: 96,
    device: "Front desk kiosk",
  },
  {
    id: "3",
    person: "Unknown face",
    employeeId: "—",
    time: "08:43:01",
    result: "Rejected",
    confidence: 42,
    device: "Front desk kiosk",
  },
];

const initials = (name: string) =>
  name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
function App() {
  const [tab, setTab] = useState<"overview" | "register" | "kiosk" | "people">(
    "overview",
  );
  const [people, setPeople] = useState<Person[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [notice, setNotice] = useState("");
  const [menu, setMenu] = useState(false);
  const [online, setOnline] = useState(false);
  const mapPerson = (p: ApiPerson): Person => ({
    ...p,
    created: new Date(p.created).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
  });
  const mapEvent = (e: ApiEvent): Event => ({
    ...e,
    time: new Date(e.at).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }),
  });
  const refresh = async () => {
    try {
      const data = await api.data();
      setPeople(data.people.map(mapPerson));
      setEvents(data.events.map(mapEvent));
      setOnline(true);
    } catch {
      setPeople(demoPeople);
      setEvents(demoEvents);
      setOnline(false);
    }
  };
  useEffect(() => {
    refresh();
    prepareFaceEngine().catch(() => {});
  }, []);
  const addPerson = async (input: {
    name: string;
    employeeId: string;
    image: string;
    embedding: number[];
    consent: boolean;
  }) => {
    const p = await api.register(input);
    setPeople((x) => [mapPerson(p), ...x]);
    setNotice(`${p.name} was securely added to the roster.`);
    setTab("people");
  };
  const navigate = (next: "overview" | "register" | "kiosk" | "people") => {
    setTab(next);
    setMenu(false);
  };
  return (
    <div className="app-shell">
      {menu && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <aside className={menu ? "open" : ""}>
        <div className="brand">
          <div className="brand-mark">V</div>
          <div>
            <strong>verity</strong>
            <span>attendance</span>
          </div>
          <button className="close-nav" onClick={() => setMenu(false)}>
            <X size={18} />
          </button>
        </div>
        <div className="workspace">
          <span className="eyebrow">Workspace</span>
          <div className="workspace-row">
            <div className="workspace-dot">A</div>
            <div>
              <b>Acme Studio</b>
              <small>Admin workspace</small>
            </div>
            <ChevronRight size={16} />
          </div>
        </div>
        <nav>
          <span className="eyebrow">Manage</span>
          <Nav
            active={tab === "overview"}
            icon={<LayoutDashboard size={18} />}
            label="Overview"
            onClick={() => navigate("overview")}
          />
          <Nav
            active={tab === "kiosk"}
            icon={<Camera size={18} />}
            label="Check-in kiosk"
            onClick={() => navigate("kiosk")}
            badge="Live"
          />
          <Nav
            active={tab === "people"}
            icon={<Users size={18} />}
            label="People"
            onClick={() => navigate("people")}
          />
          <Nav
            active={tab === "register"}
            icon={<UserPlus size={18} />}
            label="Register person"
            onClick={() => navigate("register")}
          />
          <span className="eyebrow nav-gap">System</span>
          <Nav
            active={false}
            icon={<Settings size={18} />}
            label="Settings"
            onClick={() =>
              setNotice(
                "Matching threshold: 63% · Duplicate window: 10 minutes",
              )
            }
          />
        </nav>
        <div className="side-footer">
          <div className="secure">
            <ShieldCheck size={18} />
            <div>
              <b>Privacy first</b>
              <small>Face data stored on this device</small>
            </div>
          </div>
          <div className="profile">
            <div className="avatar navy">AK</div>
            <div>
              <b>Arjun Kapoor</b>
              <small>Administrator</small>
            </div>
            <LogOut size={16} />
          </div>
        </div>
      </aside>
      <main>
        <header>
          <button
            className="mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMenu(true)}
          >
            <Menu size={20} />
          </button>
          <div>
            <span className="eyebrow">Monday, November 2, 2026</span>
            <h1>
              {tab === "overview"
                ? "Good morning, Arjun."
                : tab === "kiosk"
                  ? "Check-in kiosk"
                  : tab === "register"
                    ? "Register a person"
                    : "People directory"}
            </h1>
          </div>
          <div className="header-actions">
            <span className={"status-badge " + (online ? "online" : "offline")}>
              <i />
              {online ? "Local API online" : "Demo mode"}
            </span>
            <button
              className="button secondary"
              onClick={() => navigate("kiosk")}
            >
              <Camera size={16} /> Open kiosk
            </button>
            <div className="avatar navy">AK</div>
          </div>
        </header>
        {notice && (
          <div className="toast">
            <Check size={17} />
            {notice}
            <button onClick={() => setNotice("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {tab === "overview" && (
          <Overview people={people} events={events} go={navigate} />
        )}{" "}
        {tab === "register" && <Register onAdd={addPerson} />}{" "}
        {tab === "kiosk" && (
          <Kiosk people={people} onEvent={(e) => setEvents((x) => [e, ...x])} />
        )}{" "}
        {tab === "people" && (
          <People people={people} setPeople={setPeople} onNotice={setNotice} />
        )}
      </main>
    </div>
  );
}
function Nav({
  active,
  icon,
  label,
  onClick,
  badge,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  badge?: string;
}) {
  return (
    <button
      className={"nav-item " + (active ? "active" : "")}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
      {badge && <em>{badge}</em>}
    </button>
  );
}
function Overview({
  people,
  events,
  go,
}: {
  people: Person[];
  events: Event[];
  go: (x: "overview" | "register" | "kiosk" | "people") => void;
}) {
  const verified = events.filter((e) => e.result === "Verified");
  const avg = verified.length
    ? Math.round(
        verified.reduce((n, e) => n + e.confidence, 0) / verified.length,
      )
    : 0;
  const review = events.filter((e) => e.result !== "Verified").length;
  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow light">Attendance overview</span>
          <h2>
            Know who’s here,
            <br />
            <i>with confidence.</i>
          </h2>
          <p>
            Private face verification makes arrival simple, secure, and human.
          </p>
          <button className="button cream" onClick={() => go("kiosk")}>
            <Camera size={17} /> Start check-in <ChevronRight size={16} />
          </button>
        </div>
        <div className="hero-orbit">
          <div className="orbit o1" />
          <div className="orbit o2" />
          <div className="orbit-face">V</div>
          <span className="orbit-label">Local matching</span>
        </div>
      </section>
      <div className="stat-grid">
        <Stat
          label="Present today"
          value={verified.length.toString()}
          meta={verified.length ? "Successful check-ins" : "No check-ins yet"}
          positive={verified.length > 0}
        />
        <Stat
          label="Registered people"
          value={people.length.toString()}
          meta={
            people.length ? "Ready for attendance" : "Add your first person"
          }
        />
        <Stat
          label="Avg. confidence"
          value={`${avg}%`}
          meta={
            verified.length
              ? `Across ${verified.length} check-ins`
              : "Waiting for matches"
          }
        />
        <Stat
          label="Needs review"
          value={review.toString()}
          meta={review ? "Rejected or duplicate" : "Everything looks clear"}
          alert={review > 0}
        />
      </div>
      <div className="section-head">
        <div>
          <span className="eyebrow">Today</span>
          <h2>Recent check-ins</h2>
        </div>
        <button className="text-button" onClick={() => go("kiosk")}>
          Open kiosk <ChevronRight size={15} />
        </button>
      </div>
      <div className="table-card">
        <div className="table-head">
          <span>Person</span>
          <span>Time</span>
          <span>Result</span>
          <span>Confidence</span>
          <span>Device</span>
        </div>
        {events.length === 0 ? (
          <div className="table-empty">
            <Clock3 size={22} />
            <b>No check-ins yet</b>
            <small>Open the kiosk to record the first arrival.</small>
          </div>
        ) : (
          events.slice(0, 8).map((e) => (
            <div className="table-row" key={e.id}>
              <div className="person-cell">
                <div
                  className="avatar"
                  style={{
                    background: e.result === "Rejected" ? "#f4ded9" : "#dceee5",
                  }}
                >
                  {e.result === "Rejected" ? "?" : initials(e.person)}
                </div>
                <div>
                  <b>{e.person}</b>
                  <small>{e.employeeId}</small>
                </div>
              </div>
              <span className="muted">{e.time}</span>
              <span className={"pill " + e.result.toLowerCase()}>
                <span /> {e.result}
              </span>
              <span className="confidence">
                <b>{e.confidence}%</b>
                <i>
                  <u style={{ width: e.confidence + "%" }} />
                </i>
              </span>
              <span className="muted">{e.device}</span>
            </div>
          ))
        )}
      </div>
    </>
  );
}
function Stat({
  label,
  value,
  meta,
  positive,
  alert,
}: {
  label: string;
  value: string;
  meta: string;
  positive?: boolean;
  alert?: boolean;
}) {
  return (
    <div className="stat-card">
      <span className="eyebrow">{label}</span>
      <strong className={alert ? "alert-number" : ""}>{value}</strong>
      <small className={positive ? "positive" : ""}>
        {positive && "↗ "}
        {meta}
      </small>
    </div>
  );
}
function Register({
  onAdd,
}: {
  onAdd: (input: {
    name: string;
    employeeId: string;
    image: string;
    embedding: number[];
    consent: boolean;
  }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [consent, setConsent] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [mode, setMode] = useState<"upload" | "camera">("upload");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  useEffect(
    () => () => stream.current?.getTracks().forEach((t) => t.stop()),
    [],
  );
  const start = async () => {
    setMode("camera");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: true,
      });
      if (videoRef.current) videoRef.current.srcObject = stream.current;
    } catch {
      setMode("upload");
      alert("Camera access was not granted. You can upload an image instead.");
    }
  };
  const capture = () => {
    const c = document.createElement("canvas");
    c.width = videoRef.current?.videoWidth || 640;
    c.height = videoRef.current?.videoHeight || 480;
    c.getContext("2d")?.drawImage(videoRef.current!, 0, 0, c.width, c.height);
    setPreview(c.toDataURL("image/jpeg"));
    stream.current?.getTracks().forEach((t) => t.stop());
    setMode("upload");
  };
  const submit = async () => {
    if (!name || !employeeId || !preview || !consent) return;
    setBusy(true);
    setError("");
    try {
      const img = new Image();
      img.src = preview;
      await img.decode();
      const face = await describeEnrollment(img);
      await onAdd({
        name,
        employeeId,
        image: preview,
        embedding: face.embedding,
        consent,
      });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Registration failed. Try again.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="form-layout">
      <div className="form-intro">
        <span className="eyebrow">New registration</span>
        <h2>
          Add someone
          <br />
          <i>to the roster.</i>
        </h2>
        <p>
          Capture one clear image with only one face visible. Verity aligns 468
          facial landmarks and blends three normalized descriptors for more
          reliable matching.
        </p>
        <div className="privacy-note">
          <LockKeyhole size={18} />
          <div>
            <b>Your data stays protected</b>
            <small>
              Registration requires consent. Images stay in private local
              storage and can be deleted at any time.
            </small>
          </div>
        </div>
      </div>
      <div className="form-card">
        <div className="step-label">
          <span>01</span>Person details
        </div>
        <label>
          Full name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Anika Rao"
          />
        </label>
        <label>
          Employee or student ID
          <input
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            placeholder="e.g. EST-0241"
          />
        </label>
        <div className="step-label face-step">
          <span>02</span>Face image
        </div>
        <div className="capture-box">
          {mode === "camera" ? (
            <>
              <video ref={videoRef} autoPlay muted playsInline />
              <button className="capture" onClick={capture}>
                <Camera size={18} /> Capture image
              </button>
            </>
          ) : preview ? (
            <>
              <img src={preview} />
              <div className="image-ok">
                <Check size={14} /> Ready to analyze
              </div>
              <button className="retake" onClick={() => setPreview(null)}>
                Retake image
              </button>
            </>
          ) : (
            <>
              <div className="capture-icon">
                <FileImage size={24} />
              </div>
              <b>Upload a clear face image</b>
              <small>JPG or PNG · max 5 MB · one face only</small>
              <div className="capture-actions">
                <button
                  className="button secondary"
                  onClick={() => fileRef.current?.click()}
                >
                  <Upload size={16} /> Upload image
                </button>
                <button className="button secondary" onClick={start}>
                  <Camera size={16} /> Use camera
                </button>
              </div>
              <input
                ref={fileRef}
                hidden
                type="file"
                accept="image/png,image/jpeg"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  if (f.size >= 5e6) {
                    setError("The selected image is larger than 5 MB.");
                    return;
                  }
                  const r = new FileReader();
                  r.onload = () => setPreview(r.result as string);
                  r.readAsDataURL(f);
                }}
              />
            </>
          )}
        </div>
        {error && (
          <div className="form-error">
            <X size={16} />
            {error}
          </div>
        )}
        <label className="consent">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span>
            I have permission to register this person’s face for attendance.
          </span>
        </label>
        <button
          className="button primary full"
          disabled={!name || !employeeId || !preview || !consent || busy}
          onClick={submit}
        >
          {busy ? "Analyzing face…" : "Create registration"}{" "}
          {!busy && <ChevronRight size={17} />}
        </button>
        <small className="prototype-note">
          Face detection, liveness cues, and descriptors run locally in your
          browser.
        </small>
      </div>
    </div>
  );
}
function Kiosk({
  people,
  onEvent,
}: {
  people: Person[];
  onEvent: (e: Event) => void;
}) {
  const [active, setActive] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Event | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  useEffect(
    () => () => stream.current?.getTracks().forEach((t) => t.stop()),
    [],
  );
  const start = async () => {
    setError("");
    setResult(null);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      setActive(true);
      requestAnimationFrame(() => {
        if (video.current) video.current.srcObject = stream.current;
      });
    } catch {
      setError(
        "Camera access was denied. Allow camera access in your browser, then try again.",
      );
    }
  };
  const checkIn = async () => {
    if (!video.current) return;
    setProcessing(true);
    setError("");
    try {
      const face = await describeLiveBurst(video.current);
      const item = await api.checkIn(face.embedding);
      const mapped: Event = {
        ...item,
        time: new Date(item.at).toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }),
      };
      setResult(mapped);
      onEvent(mapped);
      stream.current?.getTracks().forEach((t) => t.stop());
      setActive(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Face verification failed.");
    } finally {
      setProcessing(false);
    }
  };
  return (
    <div className="kiosk-page">
      <div className="kiosk-copy">
        <span className="eyebrow">
          Front desk kiosk · {people.length} enrolled
        </span>
        <h2>Welcome in.</h2>
        <p>
          Look straight at the camera to check in. Your live descriptor is
          compared only against the registered roster.
        </p>
        <div className="kiosk-trust">
          <ShieldCheck size={20} />
          <span>
            <b>Private by design</b>
            <small>Video is analyzed in-browser and is never uploaded.</small>
          </span>
        </div>
        <button
          className="button primary"
          disabled={processing}
          onClick={active ? checkIn : start}
        >
          {processing
            ? "Analyzing…"
            : active
              ? "Verify & check in"
              : "Start camera"}{" "}
          {!processing && <ChevronRight size={17} />}
        </button>
        <button
          className="text-button kiosk-reset"
          onClick={() => {
            stream.current?.getTracks().forEach((t) => t.stop());
            setError("");
            setResult(null);
            setActive(false);
          }}
        >
          Reset kiosk
        </button>
      </div>
      <div className="kiosk-camera">
        {active ? (
          <>
            <video ref={video} autoPlay muted playsInline />
            <div className="face-guide">
              <span />
              <span />
              <span />
              <span />
            </div>
          </>
        ) : result ? (
          <div
            className={
              "result " + (result.result === "Verified" ? "success" : "failure")
            }
          >
            <div className="result-icon">
              {result.result === "Verified" ? (
                <Check size={28} />
              ) : (
                <X size={28} />
              )}
            </div>
            <span className="eyebrow">
              {result.result === "Verified"
                ? "Check-in complete"
                : result.result === "Duplicate"
                  ? "Already checked in"
                  : "Unable to verify"}
            </span>
            <h3>{result.person}</h3>
            <p>
              {result.result === "Verified"
                ? `Marked present at ${result.time} with ${result.confidence}% confidence.`
                : result.result === "Duplicate"
                  ? "A recent check-in already exists. No duplicate attendance was added."
                  : "Try again in brighter light or contact an administrator."}
            </p>
            <button
              className="button secondary"
              onClick={() => setResult(null)}
            >
              Continue
            </button>
          </div>
        ) : error ? (
          <div className="result failure">
            <div className="result-icon">
              <X size={28} />
            </div>
            <span className="eyebrow">Check-in paused</span>
            <h3>Let’s try that again</h3>
            <p>{error}</p>
            <button className="button secondary" onClick={start}>
              Retry camera
            </button>
          </div>
        ) : (
          <div className="camera-placeholder">
            <div className="scan-ring">
              <Camera size={30} />
            </div>
            <b>Camera ready</b>
            <small>Tap “Start camera” when ready</small>
          </div>
        )}{" "}
        {active && (
          <div className="camera-corner">LIVE · ALIGN FACE IN FRAME</div>
        )}
      </div>
    </div>
  );
}
function People({
  people,
  setPeople,
  onNotice,
}: {
  people: Person[];
  setPeople: React.Dispatch<React.SetStateAction<Person[]>>;
  onNotice: (x: string) => void;
}) {
  const remove = async (p: Person) => {
    if (!confirm(`Delete ${p.name}'s registration and biometric data?`)) return;
    try {
      await api.remove(p.id);
      setPeople((x) => x.filter((y) => y.id !== p.id));
      onNotice(`${p.name}'s registration was permanently deleted.`);
    } catch (e) {
      onNotice(
        e instanceof Error ? e.message : "Could not delete registration.",
      );
    }
  };
  return (
    <>
      <div className="section-head people-head">
        <div>
          <span className="eyebrow">Roster</span>
          <h2>
            Registered people <span className="count">{people.length}</span>
          </h2>
          <p className="section-subtitle">
            Manage consented face registrations and attendance identities.
          </p>
        </div>
        <div className="roster-chip">
          <ShieldCheck size={15} /> Encrypted local workspace
        </div>
      </div>
      {people.length === 0 ? (
        <div className="empty-state">
          <div className="capture-icon">
            <UserPlus size={24} />
          </div>
          <h3>No one is registered yet</h3>
          <p>Add the first person to start using face check-in.</p>
        </div>
      ) : (
        <div className="people-grid">
          {people.map((p) => (
            <div className="person-card" key={p.id}>
              <div className="person-top">
                <div className="big-avatar" style={{ background: p.accent }}>
                  {p.initials}
                </div>
                <button
                  className="icon-btn danger"
                  title="Delete registration"
                  onClick={() => remove(p)}
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <h3>{p.name}</h3>
              <span className="muted">{p.employeeId}</span>
              <div className="person-meta">
                <span className="pill verified">
                  <span /> {p.status}
                </span>
                <small>Added {p.created}</small>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
