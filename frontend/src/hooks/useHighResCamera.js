import { useCallback, useEffect, useRef, useState } from "react";

const HIGH_RES_CONSTRAINTS = {
  audio: false,
  video: {
    width: { ideal: 3840 },
    height: { ideal: 2160 },
    frameRate: { ideal: 30 },
    facingMode: "environment",
  },
};

/**
 * Request and manage a high-resolution camera stream.
 *
 * The hook tries to obtain a 4K stream and returns helpers for starting/stopping
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
