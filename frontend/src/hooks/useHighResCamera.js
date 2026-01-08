// Copyright (C) 2025 Goremagon
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { useCallback, useEffect, useRef, useState } from "react";

// EDITED: SAFE MODE ENABLED
// Instead of forcing 4K (which crashes many webcams), we ask for "ideal" 1080p.
// If the camera can't do 1080p, the browser will gracefully fall back to 720p 
// instead of failing completely.
const HIGH_RES_CONSTRAINTS = {
  audio: false,
  video: {
    width: { ideal: 1920 }, // Changed from 3840 (4K) to 1920 (1080p)
    height: { ideal: 1080 }, // Changed from 2160 (4K) to 1080 (1080p)
    frameRate: { ideal: 30 },
    facingMode: "environment", // Prefers back camera on phones
  },
};

/**
 * Request and manage a high-resolution camera stream.
 *
 * The hook tries to obtain a stream and returns helpers for starting/stopping
 * the camera alongside the active stream and any surfaced errors.
 */
export default function useHighResCamera() {
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const pendingRequest = useRef(null);

  const stopCamera = useCallback(() => {
    if (pendingRequest.current) {
      pendingRequest.current = null;
    }
    setStream((current) => {
      current?.getTracks().forEach((track) => track.stop());
      return null;
    });
  }, []);

  const startCamera = useCallback(async () => {
    try {
      stopCamera();
      setError(null);
      const request = navigator.mediaDevices.getUserMedia(HIGH_RES_CONSTRAINTS);
      pendingRequest.current = request;
      const mediaStream = await request;
      if (pendingRequest.current !== request) {
        // A newer request superseded this one.
        mediaStream.getTracks().forEach((track) => track.stop());
        return;
      }
      setStream(mediaStream);
    } catch (err) {
      console.error("Camera Error:", err); // Added logging to help debug
      setError(err instanceof Error ? err : new Error("Unable to start camera"));
    } finally {
      pendingRequest.current = null;
    }
  }, [stopCamera]);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, [startCamera, stopCamera]);

  return { stream, error, startCamera, stopCamera };
}
