import {
  Check,
  Cpu,
  Feather,
  Heart,
  Plus,
  Server,
  Shield,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import useHighResCamera from "../hooks/useHighResCamera";

const SCAN_INTERVAL_MS = 2000;
const TOAST_DURATION_MS = 3000;

const OPPONENTS = ["Opponent A", "Opponent B", "Opponent C"];

function Toast({ card }) {
  if (!card) return null;
  return (
    <div
      style={{
        position: "absolute",
        top: "1rem",
        right: "1rem",
        background: "rgba(17, 24, 39, 0.85)",
        color: "#fff",
        padding: "0.75rem 1rem",
        borderRadius: "0.75rem",
        boxShadow: "0 10px 25px rgba(0,0,0,0.25)",
        fontWeight: 600,
        zIndex: 20,
      }}
    >
      Card detected: {card}
    </div>
  );
}

function LifeTracker({ commanderDamage, onDamageChange, life, onLifeChange }) {
  return (
    <div
      style={{
        background: "rgba(17, 24, 39, 0.85)",
        color: "#fff",
        padding: "1rem",
        borderRadius: "0.75rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        boxShadow: "0 10px 25px rgba(0,0,0,0.25)",
      }}
    >
      <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>Life: {life}</div>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          type="button"
          onClick={() => onLifeChange(-1)}
          style={{
            flex: 1,
            padding: "0.5rem",
            borderRadius: "0.5rem",
            border: "none",
            background: "#ef4444",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          -1
        </button>
        <button
          type="button"
          onClick={() => onLifeChange(1)}
          style={{
            flex: 1,
            padding: "0.5rem",
            borderRadius: "0.5rem",
            border: "none",
            background: "#22c55e",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          +1
        </button>
      </div>
      <div style={{ fontWeight: 600 }}>Commander Damage</div>
      {OPPONENTS.map((opponent) => (
        <div
          key={opponent}
          style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          <span style={{ flex: 1 }}>{opponent}</span>
          <button
            type="button"
            onClick={() => onDamageChange(opponent, -1)}
            style={{
              width: "2rem",
              height: "2rem",
              borderRadius: "0.5rem",
              border: "none",
              background: "#ef4444",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            -
          </button>
          <span style={{ width: "2rem", textAlign: "center" }}>
            {commanderDamage[opponent]}
          </span>
          <button
            type="button"
            onClick={() => onDamageChange(opponent, 1)}
            style={{
              width: "2rem",
              height: "2rem",
              borderRadius: "0.5rem",
              border: "none",
              background: "#22c55e",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            +
          </button>
        </div>
      ))}
    </div>
  );
}

function CandidatePicker({ candidates, onSelect }) {
  if (!candidates?.length) return null;
  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.9)",
        padding: "1rem",
        borderRadius: "0.75rem",
        color: "#fff",
        display: "grid",
        gap: "0.75rem",
      }}
    >
      <div style={{ fontWeight: 600 }}>Low confidence. Pick a match:</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: "0.5rem" }}>
        {candidates.map((candidate) => (
          <button
            key={`${candidate.card}-${candidate.set}`}
            type="button"
            onClick={() => onSelect(candidate)}
            style={{
              border: "1px solid rgba(148, 163, 184, 0.4)",
              borderRadius: "0.5rem",
              overflow: "hidden",
              background: "#0f172a",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            {candidate.image_url ? (
              <img
                src={candidate.image_url}
                alt={candidate.card}
                style={{ width: "100%", height: "120px", objectFit: "cover" }}
              />
            ) : (
              <div style={{ padding: "0.5rem", height: "120px" }}>{candidate.card}</div>
            )}
            <div style={{ padding: "0.25rem", fontSize: "0.75rem" }}>{candidate.card}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function OverlayCounters({ counters, keywords, onCounterChange, onKeywordToggle }) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: "1rem",
        right: "1rem",
        background: "rgba(15, 23, 42, 0.9)",
        padding: "0.75rem",
        borderRadius: "0.75rem",
        color: "#fff",
        display: "grid",
        gap: "0.5rem",
        zIndex: 15,
      }}
    >
      <div style={{ fontWeight: 600 }}>Card Counters</div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <button
          type="button"
          onClick={() => onCounterChange(-1)}
          style={{
            width: "2rem",
            height: "2rem",
            borderRadius: "0.5rem",
            border: "none",
            background: "#ef4444",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          -
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          <Plus size={16} />
          {counters}
        </div>
        <button
          type="button"
          onClick={() => onCounterChange(1)}
          style={{
            width: "2rem",
            height: "2rem",
            borderRadius: "0.5rem",
            border: "none",
            background: "#22c55e",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          +
        </button>
      </div>
      <div style={{ fontWeight: 600 }}>Keywords</div>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          type="button"
          onClick={() => onKeywordToggle("Flying")}
          style={{
            borderRadius: "999px",
            border: "1px solid rgba(148, 163, 184, 0.4)",
            padding: "0.25rem 0.5rem",
            background: keywords.includes("Flying") ? "#3b82f6" : "#0f172a",
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.25rem",
          }}
        >
          <Feather size={14} /> Flying
        </button>
        <button
          type="button"
          onClick={() => onKeywordToggle("Lifelink")}
          style={{
            borderRadius: "999px",
            border: "1px solid rgba(148, 163, 184, 0.4)",
            padding: "0.25rem 0.5rem",
            background: keywords.includes("Lifelink") ? "#ec4899" : "#0f172a",
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.25rem",
          }}
        >
          <Heart size={14} /> Lifelink
        </button>
        <button
          type="button"
          onClick={() => onKeywordToggle("Ward")}
          style={{
            borderRadius: "999px",
            border: "1px solid rgba(148, 163, 184, 0.4)",
            padding: "0.25rem 0.5rem",
            background: keywords.includes("Ward") ? "#f97316" : "#0f172a",
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.25rem",
          }}
        >
          <Shield size={14} /> Ward
        </button>
      </div>
    </div>
  );
}

export default function GameRoom() {
  const { stream, error } = useHighResCamera();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [detectedCard, setDetectedCard] = useState(null);
  const [candidateMatches, setCandidateMatches] = useState([]);
  const [mode, setMode] = useState("play");
  const [decklist, setDecklist] = useState("");
  const [deckStatus, setDeckStatus] = useState(null);
  const [computeSource, setComputeSource] = useState("local");
  const [networkHost, setNetworkHost] = useState("http://localhost:8000");
  const [lobbyCode, setLobbyCode] = useState("");
  const [joinedLobby, setJoinedLobby] = useState(false);
  const [overlayImage, setOverlayImage] = useState(null);
  const [counterValue, setCounterValue] = useState(0);
  const [keywords, setKeywords] = useState([]);
  const [commanderDamage, setCommanderDamage] = useState(
    Object.fromEntries(OPPONENTS.map((opponent) => [opponent, 0]))
  );
  const [life, setLife] = useState(40);
  const toastTimeout = useRef(null);

  const apiBase = computeSource === "network" ? networkHost : "/api";

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onWheel = (event) => event.preventDefault();
    document.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      document.body.style.overflow = originalOverflow;
      document.removeEventListener("wheel", onWheel);
    };
  }, []);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  useEffect(() => {
    if (!stream) return undefined;

    const scan = async () => {
      if (!videoRef.current) return;
      const video = videoRef.current;

      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;

      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
      const base64 = dataUrl.replace(/^data:image\/\w+;base64,/, "");

      try {
        const response = await fetch(`${apiBase}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: base64, mode }),
        });
        if (!response.ok) return;
        const payload = await response.json();
        if (payload?.match && payload.card) {
          setDetectedCard(payload.card);
          setCandidateMatches(payload.candidates || []);
          clearTimeout(toastTimeout.current);
          toastTimeout.current = setTimeout(() => setDetectedCard(null), TOAST_DURATION_MS);
          setOverlayImage(payload.candidates?.[0]?.image_url || payload.image_url || null);
        } else if (payload?.candidates?.length) {
          setCandidateMatches(payload.candidates);
        }
      } catch (err) {
        console.error("Scan failed:", err);
      }
    };

    const intervalId = setInterval(scan, SCAN_INTERVAL_MS);
    return () => {
      clearInterval(intervalId);
      clearTimeout(toastTimeout.current);
    };
  }, [stream, mode, apiBase]);

  const overlayMessage = useMemo(() => {
    if (error) return "Camera unavailable. Please allow access.";
    if (!stream) return "Requesting high-resolution camera…";
    return null;
  }, [error, stream]);

  const handleLoadDeck = async () => {
    try {
      const response = await fetch(`${apiBase}/load-deck`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decklist }),
      });
      if (!response.ok) {
        setDeckStatus("Failed to load deck.");
        return;
      }
      setDeckStatus("Deck loaded.");
    } catch (err) {
      setDeckStatus("Failed to load deck.");
      console.error("Deck load failed:", err);
    }
  };

  const handleCandidateSelect = (candidate) => {
    setDetectedCard(candidate.card);
    setOverlayImage(candidate.image_url || null);
    setCandidateMatches([]);
  };

  const handleDamageChange = (opponent, delta) => {
    setCommanderDamage((prev) => {
      const next = Math.max(0, prev[opponent] + delta);
      setLife((current) => current - delta);
      return { ...prev, [opponent]: next };
    });
  };

  const handleLifeChange = (delta) => {
    setLife((current) => current + delta);
  };

  const handleCounterChange = (delta) => {
    setCounterValue((current) => Math.max(0, current + delta));
  };

  const handleKeywordToggle = (keyword) => {
    setKeywords((current) =>
      current.includes(keyword)
        ? current.filter((item) => item !== keyword)
        : [...current, keyword]
    );
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        background: "#0b132b",
        display: "flex",
        gap: "1rem",
        padding: "1rem",
        boxSizing: "border-box",
      }}
    >
      <div style={{ flex: 3, position: "relative" }}>
        <div
          style={{
            position: "relative",
            width: "100%",
            height: "100%",
            borderRadius: "0.75rem",
            overflow: "hidden",
            boxShadow: "0 20px 45px rgba(0,0,0,0.45)",
            background: "#111827",
          }}
        >
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              opacity: overlayImage ? 0.6 : 1,
              transition: "opacity 0.4s ease",
            }}
          />
          {overlayImage && (
            <img
              src={overlayImage}
              alt="Detected card"
              style={{
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
                objectFit: "contain",
                opacity: 0.4,
                transition: "opacity 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease",
                boxShadow: "0 0 0 rgba(0,0,0,0)",
              }}
              onMouseEnter={(event) => {
                event.currentTarget.style.opacity = "1";
                event.currentTarget.style.transform = "scale(1.8)";
                event.currentTarget.style.boxShadow = "0 30px 60px rgba(0,0,0,0.6)";
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.opacity = "0.4";
                event.currentTarget.style.transform = "scale(1)";
                event.currentTarget.style.boxShadow = "0 0 0 rgba(0,0,0,0)";
              }}
            />
          )}
          <OverlayCounters
            counters={counterValue}
            keywords={keywords}
            onCounterChange={handleCounterChange}
            onKeywordToggle={handleKeywordToggle}
          />
          <Toast card={detectedCard} />
        </div>
        <canvas ref={canvasRef} style={{ display: "none" }} aria-hidden="true" />
      </div>

      <div
        style={{
          flex: 1.2,
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          color: "#fff",
        }}
      >
        <div
          style={{
            background: "rgba(15, 23, 42, 0.9)",
            padding: "1rem",
            borderRadius: "0.75rem",
            display: "grid",
            gap: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Users size={18} /> Lobby Code
          </div>
          <input
            value={lobbyCode}
            onChange={(event) => setLobbyCode(event.target.value)}
            placeholder="Enter lobby code"
            style={{
              padding: "0.5rem",
              borderRadius: "0.5rem",
              border: "1px solid rgba(148, 163, 184, 0.4)",
              background: "#0f172a",
              color: "#fff",
            }}
          />
          <button
            type="button"
            onClick={() => setJoinedLobby(Boolean(lobbyCode))}
            style={{
              padding: "0.5rem",
              borderRadius: "0.5rem",
              border: "none",
              background: "#3b82f6",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            {joinedLobby ? "Connected" : "Join Lobby"}
          </button>
        </div>

        <div
          style={{
            background: "rgba(15, 23, 42, 0.9)",
            padding: "1rem",
            borderRadius: "0.75rem",
            display: "grid",
            gap: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Cpu size={18} /> Compute Source
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="radio"
              checked={computeSource === "local"}
              onChange={() => setComputeSource("local")}
            />
            <span>Local</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="radio"
              checked={computeSource === "network"}
              onChange={() => setComputeSource("network")}
            />
            <span>Network Host</span>
          </label>
          {computeSource === "network" && (
            <div style={{ display: "grid", gap: "0.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Server size={16} /> Host URL
              </div>
              <input
                value={networkHost}
                onChange={(event) => setNetworkHost(event.target.value)}
                style={{
                  padding: "0.5rem",
                  borderRadius: "0.5rem",
                  border: "1px solid rgba(148, 163, 184, 0.4)",
                  background: "#0f172a",
                  color: "#fff",
                }}
              />
            </div>
          )}
        </div>

        <div
          style={{
            background: "rgba(15, 23, 42, 0.9)",
            padding: "1rem",
            borderRadius: "0.75rem",
            display: "grid",
            gap: "0.75rem",
          }}
        >
          <div style={{ fontWeight: 600 }}>Mode</div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={() => setMode("play")}
              style={{
                flex: 1,
                padding: "0.5rem",
                borderRadius: "0.5rem",
                border: "none",
                cursor: "pointer",
                background: mode === "play" ? "#3b82f6" : "#1f2937",
                color: "#fff",
              }}
            >
              Play
            </button>
            <button
              type="button"
              onClick={() => setMode("collection")}
              style={{
                flex: 1,
                padding: "0.5rem",
                borderRadius: "0.5rem",
                border: "none",
                cursor: "pointer",
                background: mode === "collection" ? "#3b82f6" : "#1f2937",
                color: "#fff",
              }}
            >
              Collection
            </button>
          </div>
          <label style={{ fontSize: "0.85rem", fontWeight: 600 }}>Load Decklist</label>
          <textarea
            value={decklist}
            onChange={(event) => setDecklist(event.target.value)}
            rows={4}
            placeholder="Paste decklist here..."
            style={{
              resize: "none",
              borderRadius: "0.5rem",
              border: "1px solid rgba(148, 163, 184, 0.4)",
              padding: "0.5rem",
              background: "#0f172a",
              color: "#fff",
            }}
          />
          <button
            type="button"
            onClick={handleLoadDeck}
            style={{
              padding: "0.5rem",
              borderRadius: "0.5rem",
              border: "none",
              background: "#22c55e",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            <Check size={16} style={{ marginRight: "0.25rem" }} /> Load Deck
          </button>
          {deckStatus && <div style={{ fontSize: "0.8rem" }}>{deckStatus}</div>}
        </div>

        <LifeTracker
          commanderDamage={commanderDamage}
          onDamageChange={handleDamageChange}
          life={life}
          onLifeChange={handleLifeChange}
        />

        <CandidatePicker candidates={candidateMatches} onSelect={handleCandidateSelect} />

        <div
          style={{
            background: "rgba(15, 23, 42, 0.9)",
            padding: "1rem",
            borderRadius: "0.75rem",
            display: "grid",
            gap: "0.5rem",
          }}
        >
          <div style={{ fontWeight: 600 }}>Gallery</div>
          {OPPONENTS.map((opponent) => (
            <div
              key={opponent}
              style={{
                background: "#1f2937",
                borderRadius: "0.5rem",
                padding: "0.5rem",
                minHeight: "80px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>{opponent}</span>
              <span style={{ fontSize: "0.75rem", opacity: 0.7 }}>Video stub</span>
            </div>
          ))}
        </div>
      </div>

      {overlayMessage && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0, 0, 0, 0.4)",
            color: "#fff",
            fontSize: "1rem",
            zIndex: 30,
          }}
        >
          {overlayMessage}
        </div>
      )}
    </div>
  );
}
