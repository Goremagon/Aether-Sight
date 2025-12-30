import { useEffect, useRef, useState } from "react";

// --- COMPONENTS ---
function Toast({ card, isScanning }) {
  if (isScanning) {
    return (
      <div style={{
        position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
        background: "rgba(34, 197, 94, 0.2)", border: "4px solid #22c55e",
        padding: "2rem", borderRadius: "1rem", color: "#fff", fontWeight: 700,
        boxShadow: "0 0 50px #22c55e", zIndex: 100, backdropFilter: "blur(4px)"
      }}>
        SCANNING TARGET...
      </div>
    );
  }

  if (!card) return null;
  
  return (
    <div style={{
      position: "absolute", top: "2rem", left: "50%", transform: "translateX(-50%)",
      background: "rgba(17, 24, 39, 0.95)", color: "#fff",
      padding: "1rem 2rem", borderRadius: "1rem",
      boxShadow: "0 20px 50px rgba(0,0,0,0.5)", fontWeight: 700,
      fontSize: "2rem", zIndex: 100, border: "2px solid #22c55e",
      animation: "popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)"
    }}>
      ✅ {card}
    </div>
  );
}

function LifeCounter() {
  const [life, setLife] = useState(40);
  return (
    <div style={{
      position: "absolute", bottom: "1rem", left: "1rem",
      background: "rgba(17, 24, 39, 0.85)", color: "#fff",
      padding: "0.75rem 1rem", borderRadius: "0.75rem",
      display: "flex", alignItems: "center", gap: "0.75rem",
      boxShadow: "0 10px 25px rgba(0,0,0,0.25)", zIndex: 100
    }}>
      <button onClick={(e) => { e.stopPropagation(); setLife(l => l - 1) }} style={{
        width: "3rem", height: "3rem", borderRadius: "0.5rem",
        background: "#ef4444", border: "none", color: "#fff", fontSize: "1.5rem", cursor: "pointer"
      }}>-</button>
      <div style={{ fontSize: "2.5rem", fontWeight: 700, minWidth: "4rem", textAlign: "center" }}>{life}</div>
      <button onClick={(e) => { e.stopPropagation(); setLife(l => l + 1) }} style={{
        width: "3rem", height: "3rem", borderRadius: "0.5rem",
        background: "#22c55e", border: "none", color: "#fff", fontSize: "1.5rem", cursor: "pointer"
      }}>+</button>
    </div>
  );
}

// --- MAIN SCREEN ---
export default function GameRoom() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [detectedCard, setDetectedCard] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  
  useEffect(() => {
    async function startCamera() {
      try {
        const constraints = { 
          video: { width: { min: 1280, ideal: 1920 }, height: { min: 720, ideal: 1080 } }, 
          audio: false 
        };
        const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
        setStream(mediaStream);
        if (videoRef.current) videoRef.current.srcObject = mediaStream;
      } catch (err) {
        console.error("Camera Error:", err);
      }
    }
    startCamera();
    return () => { if (stream) stream.getTracks().forEach(track => track.stop()); };
  }, []);

  // --- THE NEW CLICK HANDLER ---
  const handleScanClick = async (e) => {
    if (isScanning || !videoRef.current || !canvasRef.current) return;
    
    setIsScanning(true);
    setDetectedCard(null);

    const video = videoRef.current;
    
    // 1. Calculate Click Position as Percentage (0.0 to 1.0)
    // This handles resizing windows perfectly.
    const rect = e.target.getBoundingClientRect();
    const xPercent = (e.clientX - rect.left) / rect.width;
    const yPercent = (e.clientY - rect.top) / rect.height;

    // 2. Capture Frame
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64 = canvas.toDataURL("image/jpeg", 0.9).split(",")[1];

    try {
      const res = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // 3. Send Image + Target Coordinates
        body: JSON.stringify({ 
            image: base64,
            target_x: xPercent,
            target_y: yPercent
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.match) {
          console.log("MATCH:", data.card);
          setDetectedCard(data.card);
        } else {
            console.log("No match found.");
        }
      }
    } catch (e) {
      console.error("Scan failed", e);
    } finally {
        setIsScanning(false);
    }
  };

  return (
    <div 
      onClick={handleScanClick}
      style={{
        position: "relative", width: "100vw", height: "100vh",
        background: "#0b132b", overflow: "hidden",
        display: "flex", justifyContent: "center", alignItems: "center",
        cursor: "crosshair"
      }}
    >
      <video ref={videoRef} autoPlay playsInline muted style={{
        width: "100%", height: "100%", objectFit: "cover",
        opacity: isScanning ? 0.5 : 1
      }} />
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {!detectedCard && !isScanning && (
         <div style={{
             position: "absolute", top: "10%", 
             background: "rgba(0,0,0,0.5)", color: "rgba(255,255,255,0.7)",
             padding: "0.5rem 1rem", borderRadius: "1rem", pointerEvents: "none"
         }}>
             Click a card to identify it
         </div>
      )}
      <Toast card={detectedCard} isScanning={isScanning} />
      <LifeCounter />
    </div>
  );
}