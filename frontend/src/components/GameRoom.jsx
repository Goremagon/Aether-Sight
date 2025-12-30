import { useEffect, useMemo, useRef, useState } from "react";
import useHighResCamera from "../hooks/useHighResCamera";

const SCAN_INTERVAL_MS = 2000;
const TOAST_DURATION_MS = 3000;

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
      }}
    >
      Card detected: {card}
    </div>
  );
}

function LifeCounter() {
  const [life, setLife] = useState(40);
  return (
    <div
      style={{
        position: "absolute",
        bottom: "1rem",
        left: "1rem",
        background: "rgba(17, 24, 39, 0.85)",
        color: "#fff",
        padding: "0.75rem 1rem",
        borderRadius: "0.75rem",
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        boxShadow: "0 10px 25px rgba(0,0,0,0.25)",
      }}
    >
      <button
        type="button"
        onClick={() => setLife((l) => l - 1)}
        style={{
          width: "2.25rem",
          height: "2.25rem",
          borderRadius: "0.5rem",
          background: "#ef4444",
          border: "none",
          color: "#fff",
          fontSize: "1.25rem",
          cursor: "pointer",
        }}
        aria-label="Decrease life"
      >
        -
      </button>
      <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{life}</div>
      <button
        type="button"
        onClick={() => setLife((l) => l + 1)}
        style={{
          width: "2.25rem",
          height: "2.25rem",
          borderRadius: "0.5rem",
          background: "#22c55e",
          border: "none",
          color: "#fff",
          fontSize: "1.25rem",
          cursor: "pointer",
        }}
        aria-label="Increase life"
      >
        +
      </button>
    </div>
  );
}

export default function GameRoom() {
  const { stream, error } = useHighResCamera();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [detectedCard, setDetectedCard] = useState(null);
  const toastTimeout = useRef(null);

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
        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: base64 }),
        });
        if (!response.ok) return;
        const payload = await response.json();
        if (payload?.match && payload.card) {
          setDetectedCard(payload.card);
          clearTimeout(toastTimeout.current);
          toastTimeout.current = setTimeout(() => setDetectedCard(null), TOAST_DURATION_MS);
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
  }, [stream]);

  const overlayMessage = useMemo(() => {
    if (error) return "Camera unavailable. Please allow access.";
    if (!stream) return "Requesting high-resolution camera…";
    return null;
  }, [error, stream]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100vh",
        background: "#0b132b",
        overflow: "hidden",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
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
          borderRadius: "0.75rem",
          boxShadow: "0 20px 45px rgba(0,0,0,0.45)",
        }}
      />

      <canvas ref={canvasRef} style={{ display: "none" }} aria-hidden="true" />

      {overlayMessage && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            background: "rgba(17, 24, 39, 0.8)",
            color: "#fff",
            padding: "1rem 1.5rem",
            borderRadius: "0.75rem",
            fontSize: "1rem",
            boxShadow: "0 10px 25px rgba(0,0,0,0.3)",
          }}
        >
          {overlayMessage}
        </div>
      )}

      <Toast card={detectedCard} />
      <LifeCounter />
    </div>
  );
}
