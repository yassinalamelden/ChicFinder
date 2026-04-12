import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import { Upload, Camera, Image as ImageIcon } from 'lucide-react';

export interface ImageCaptureProps {
  /**
   * Callback fired when an image is successfully captured or uploaded.
   * Returns a clean Base64 string WITHOUT the data URI prefix.
   */
  onImageReady: (base64: string) => void;
}

export const ImageCapture: React.FC<ImageCaptureProps> = ({ onImageReady }) => {
  const [mode, setMode] = useState<'upload' | 'camera'>('upload');
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const webcamRef = useRef<Webcam>(null);

  const processBase64 = (dataUrl: string) => {
    try {
      // The prefix looks like "data:image/jpeg;base64,"
      // Splitting by "," and taking the second element gives us the raw base64 data
      const cleanBase64 = dataUrl.split(',')[1];
      if (cleanBase64) {
        onImageReady(cleanBase64);
        setError(null);
      } else {
        throw new Error('Invalid base64 string format');
      }
    } catch (err) {
      setError('Failed to process image. Please try again.');
      console.error('Error processing base64 image:', err);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Basic validation for image formats
      if (!file.type.match(/^image\/(jpeg|png|jpg)$/)) {
        setError('Please upload a valid JPG or PNG image.');
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        setPreview(result);
        processBase64(result);
      };
      reader.onerror = () => {
        setError('Failed to read file.');
      };
      reader.readAsDataURL(file);
    }
  };

  const capturePhoto = useCallback(() => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        setPreview(imageSrc);
        processBase64(imageSrc);
      } else {
        setError('Failed to capture photo from webcam.');
      }
    }
  }, [webcamRef, onImageReady]);

  const switchMode = (newMode: 'upload' | 'camera') => {
    setMode(newMode);
    setPreview(null);
    setError(null);
  };

  return (
    <div className="w-full max-w-md p-4 bg-white rounded-xl shadow-sm border border-gray-200">
      {/* Tab Navigation */}
      <div className="flex gap-2 mb-4 bg-gray-50 p-1 rounded-lg border border-gray-100">
        <button
          onClick={() => switchMode('upload')}
          className={`flex-1 py-2 px-4 flex items-center justify-center gap-2 rounded-md font-medium text-sm transition-all duration-200 ${mode === 'upload'
              ? 'bg-white text-blue-700 shadow-sm border border-gray-200'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
        >
          <Upload size={18} />
          Upload File
        </button>
        <button
          onClick={() => switchMode('camera')}
          className={`flex-1 py-2 px-4 flex items-center justify-center gap-2 rounded-md font-medium text-sm transition-all duration-200 ${mode === 'camera'
              ? 'bg-white text-blue-700 shadow-sm border border-gray-200'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
        >
          <Camera size={18} />
          Use Camera
        </button>
      </div>

      {/* Error Message Display */}
      {error && (
        <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md">
          {error}
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex flex-col items-center justify-center min-h-[300px] border-2 border-dashed border-gray-300 rounded-lg p-4 bg-gray-50">

        {/* Upload Mode */}
        {mode === 'upload' && !preview && (
          <div className="flex flex-col items-center gap-4">
            <div className="p-4 bg-blue-50 focus-within:ring-4 ring-blue-100 rounded-full text-blue-600">
              <ImageIcon size={32} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700 mb-1">Upload an image file</p>
              <p className="text-xs text-gray-500 mb-4">Supports .jpg, .jpeg, .png</p>
            </div>
            <label className="cursor-pointer bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors focus:ring-4 focus:ring-blue-100 shadow-sm">
              Select Image
              <input
                type="file"
                accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        )}

        {/* Camera Mode */}
        {mode === 'camera' && !preview && (
          <div className="flex flex-col items-center w-full gap-4">
            <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-black shadow-inner border border-gray-200">
              {/* @ts-ignore - Some versions of react-webcam have conflicting prop types, safely ignoring */}
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                videoConstraints={{ facingMode: "user" }}
                className="w-full h-full object-cover"
                onUserMediaError={() => setError('Camera access denied or unavailable.')}
              />
            </div>
            <button
              onClick={capturePhoto}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors w-full flex items-center justify-center gap-2 shadow-sm"
            >
              <Camera size={18} />
              Capture Photo
            </button>
          </div>
        )}

        {/* Selected/Captured Image Preview */}
        {preview && (
          <div className="flex flex-col items-center justify-center w-full h-full gap-4">
            <div className="relative rounded-lg overflow-hidden border border-gray-200 shadow-sm max-w-full">
              <img src={preview} alt="Captured preview" className="max-h-[250px] w-auto object-contain" />
            </div>
            <button
              onClick={() => setPreview(null)}
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors underline underline-offset-4"
            >
              Take another one
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
