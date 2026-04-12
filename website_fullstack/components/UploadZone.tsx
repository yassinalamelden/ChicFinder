"use client";

import { useRef, useState } from "react";
import { Camera, Upload, X } from "lucide-react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  isLoading?: boolean;
}

export function UploadZone({ onFileSelected, isLoading = false }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

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
            onClick={() => cameraInputRef.current?.click()}
            className="flex-1 flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-white/80 hover:text-white py-3 px-5 transition-colors text-sm"
          >
            <Camera className="w-4 h-4" />
            Take Photo
          </button>
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
    </div>
  );
}
