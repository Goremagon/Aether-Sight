// Copyright (C) 2025 Goremagon
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { useEffect, useRef, useState } from "react";

// --- COMPONENTS ---
function CardInfoPanel({ cardName, onClose }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!cardName) return;
    fetch(`https://api.scryfall.com/cards/named?exact=${encodeURIComponent(cardName)}`)
      .then(res => res.json())
      .then(setData)
      .catch(e => console.error(e));
  }, [cardName]);

  const isOpen = !!cardName;

  return (
    <div style={{
      position: "absolute", top: 0, right: 0, bottom: 0, width: "350px",
      background: "rgba(11, 19, 43, 0.95)", borderLeft: "2px solid #22c55e",
      padding: "2rem", color: "#fff", display: "flex", flexDirection: "column",
      gap: "1.5rem", boxShadow: "-10px 0 30px rgba(0,0,0,0.5)",
      transition: "transform 0.3s ease", 
      transform: isOpen ? "translateX(0)" : "translateX(100%)",
      overflowY: "auto", zIndex: 50
    }}>
      <button 
        onClick={onClose}
        style={{
          position: "absolute", top: "1rem", right: "1rem",
          background: "transparent", border: "none", color: "#fff",
          fontSize: "1.5rem", cursor: "pointer", fontWeight: "bold"
        }}
      >
        ✕
      </button>

      {data && (
        <>
          <h2 style={{ fontSize: "2rem", margin: "1rem 0 0 0", borderBottom: "1px solid #444", paddingBottom: "1rem" }}>
            {data.name}
          </h2>
          
          {data.image_uris && (
            <img 
              src={data.image_uris.normal} 
              alt={data.name} 
              style={{ width: "100%", borderRadius: "1rem", boxShadow: "0 10px 20px rgba(0,0,0,0.5)" }} 
            />
          )}
          <div style={{ background: "rgba(255,255,255,0.1)", padding: "1rem", borderRadius: "0.5rem", lineHeight: "1.6" }}>
            <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{data.oracle_text}</p>
          </div>
        </>
      )}
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
  const [rotation, setRotation] = useState(180); 
  
  // --- AR SCANNER STATE ---
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  // Initial width in pixels. 
  // MTG Aspect Ratio: 63mm / 88mm = 0.716
  const [boxWidth, setBoxWidth] = useState(250); 
  const boxHeight = boxWidth / 0.716; 

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
      } catch (err) { console.error("Camera Error:", err); }
    }
    startCamera();
    return () => { if (stream) stream.getTracks().forEach(track => track.stop()); };
  }, []);

  // Handle Scroll to Resize Box
  const handleWheel = (e) => {
      // Prevent page scroll
      if(e.deltaY !== 0) {
          setBoxWidth(prev => Math.max(100, Math.min(600, prev - e.deltaY * 0.5)));
      }
  };

  const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
  }

  const handleScanClick = async (e) => {
    if (e.target.tagName === "BUTTON") return;
    if (isScanning || e.target.closest("div[style*='right: 0']")) return;
    if (detectedCard) { setDetectedCard(null); return; }
    if (!videoRef.current || !canvasRef.current) return;

    setIsScanning(true);
    const video = videoRef.current;
    const rect = e.target.getBoundingClientRect();
    
    // Send absolute click coordinates
    const xPercent = (e.clientX - rect.left) / rect.width;
    const yPercent = (e.clientY - rect.top) / rect.height;
    
    // Send the SCALE (Box Width relative to Video Width)
    // This tells backend exactly how big the card is in pixels
    const widthPercent = boxWidth / rect.width;

    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");

    ctx.save();
    if (rotation === 180) {
      ctx.translate(canvas.width, canvas.height);
      ctx.rotate(Math.PI); 
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    // High Quality PNG
    const base64 = canvas.toDataURL("image/png").split(",")[1];

    try {
      const res = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            image: base64, 
            target_x: xPercent, 
            target_y: yPercent,
            box_scale: widthPercent // Tell backend the size
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.match) setDetectedCard(data.card);
      }
    } catch (e) { console.error("Scan failed", e); } 
    finally { setIsScanning(false); }
  };

  return (
    <div 
        onClick={handleScanClick} 
        onMouseMove={handleMouseMove}
        onWheel={handleWheel}
        style={{
            position: "relative", width: "100vw", height: "100vh", background: "#0b132b", 
            overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "center",
            cursor: "none" // Hide default cursor, we use the box!
        }}
    >
      <video ref={videoRef} autoPlay playsInline muted style={{
        width: "100%", height: "100%", objectFit: "contain",
        opacity: isScanning ? 0.5 : 1, transform: `rotate(${rotation}deg)`, transition: "transform 0.5s ease"
      }} />
      <canvas ref={canvasRef} style={{ display: "none" }} />
      
      {/* THE AR SCANNER BOX */}
      {!detectedCard && (
          <div style={{
              position: "fixed",
              left: mousePos.x - boxWidth / 2,
              top: mousePos.y - boxHeight / 2,
              width: boxWidth,
              height: boxHeight,
              border: "2px solid #ef4444",
              boxShadow: "0 0 10px #ef4444, inset 0 0 20px rgba(239, 68, 68, 0.3)",
              borderRadius: "4px",
              pointerEvents: "none", // Let clicks pass through
              zIndex: 10
          }}>
              {/* Center Crosshair */}
              <div style={{ position: "absolute", top: "50%", left: "50%", width: "4px", height: "4px", background: "#ef4444", transform: "translate(-50%, -50%)", borderRadius: "50%"}} />
              
              {/* Helper Text */}
              <div style={{ position: "absolute", bottom: "-25px", left: "0", width: "100%", textAlign: "center", color: "white", fontSize: "0.8rem", textShadow: "0 1px 2px black" }}>
                  Scroll to Resize
              </div>
          </div>
      )}

      <button onClick={(e) => { e.stopPropagation(); setRotation(r => (r === 0 ? 180 : 0)); }}
        style={{
            position: "absolute", top: "1rem", left: "1rem", zIndex: 200, cursor: "pointer",
            background: "rgba(255,255,255,0.1)", color: "#fff", border: "1px solid #fff",
            padding: "0.5rem 1rem", borderRadius: "0.5rem"
        }}>↻ Flip Camera</button>
      
      <CardInfoPanel cardName={detectedCard} onClose={() => setDetectedCard(null)} />
      <LifeCounter />
    </div>
  );
}