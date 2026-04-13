"use client";

import { useRef, useState, useEffect } from "react";
import { Camera, Upload, X, RotateCw } from "lucide-react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  isLoading?: boolean;
}

export function UploadZone({ onFileSelected, isLoading = false }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [preview, setPreview] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [stream, setStream] = useState<MediaStream | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    setPendingFile(file);
    // reset input so same file can be re-selected
    e.target.value = "";
  };

  const handleSearch = () => {
    if (pendingFile) onFileSelected(pendingFile);
  };

  const handleClear = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setPendingFile(null);
  };

  // Set srcObject after the video element mounts (cameraOpen renders it into the DOM)
  useEffect(() => {
    if (cameraOpen && videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [cameraOpen, stream]);

  const openCamera = async (overrideFacingMode?: "environment" | "user") => {
    const mode = overrideFacingMode ?? facingMode;
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: mode } },
      });
      setStream(mediaStream);
      setCameraOpen(true);
    } catch (error) {
      console.warn("getUserMedia not available or denied, falling back to capture input:", error);
      cameraInputRef.current?.click();
    }
  };

  const closeCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setCameraOpen(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" });
          const url = URL.createObjectURL(file);
          setPreview(url);
          setPendingFile(file);
        }
        closeCamera();
      },
      "image/jpeg",
      0.92
    );
  };

  const flipCamera = async () => {
    closeCamera();
    const newMode = facingMode === "environment" ? "user" : "environment";
    setFacingMode(newMode);
    openCamera(newMode);
  };

  return (
    <div className="flex flex-col items-center gap-4 w-full max-w-md mx-auto">
      {preview ? (
        /* Image preview + search CTA */
        <div className="w-full space-y-3">
          <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-white/5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={preview}
              alt="Selected outfit"
              className="w-full max-h-64 object-contain"
            />
            <button
              onClick={handleClear}
              className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center transition-colors"
              aria-label="Remove image"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
          <button
            onClick={handleSearch}
            disabled={isLoading}
            className="w-full rounded-full bg-white text-black font-semibold py-3 hover:bg-white/90 transition-colors disabled:opacity-60"
          >
            {isLoading ? "Searching..." : "Find Similar Items →"}
          </button>
        </div>
      ) : (
        /* Upload / Camera buttons */
        <div className="flex gap-3 w-full">
          {/* File upload */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex-1 flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-white/80 hover:text-white py-3 px-5 transition-colors text-sm"
          >
            <Upload className="w-4 h-4" />
            Upload Photo
          </button>

          {/* Camera capture */}
          <button
            onClick={openCamera}
            className="flex-1 flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-white/80 hover:text-white py-3 px-5 transition-colors text-sm"
          >
            <Camera className="w-4 h-4" />
            Take Photo
          </button>
        </div>
      )}

      {/* Camera Modal */}
      {cameraOpen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center">
          {/* Live video feed */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />

          {/* Controls overlay at bottom */}
          <div className="absolute bottom-8 left-0 right-0 flex items-center justify-center gap-6">
            {/* Close button */}
            <button
              onClick={closeCamera}
              className="w-12 h-12 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center transition-colors"
              aria-label="Close camera"
            >
              <X className="w-6 h-6 text-white" />
            </button>

            {/* Capture button (shutter) */}
            <button
              onClick={capturePhoto}
              className="w-16 h-16 rounded-full bg-white hover:bg-white/90 flex items-center justify-center transition-colors shadow-lg"
              aria-label="Capture photo"
            >
              <div className="w-14 h-14 rounded-full border-4 border-black/30" />
            </button>

            {/* Flip camera button */}
            <button
              onClick={flipCamera}
              className="w-12 h-12 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center transition-colors"
              aria-label="Flip camera"
            >
              <RotateCw className="w-6 h-6 text-white" />
            </button>
          </div>
        </div>
      )}

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Hidden canvas for photo capture */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
