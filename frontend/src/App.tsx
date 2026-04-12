import React from 'react'
import { ImageCapture } from '@/components/ImageCapture'

function App() {
  const handleImageReady = (base64: string) => {
    console.log('Image successfully captured! Base64 string length:', base64.length)
    alert('Image captured successfully! See console for Base64 data.')
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">ChicFinder Image Capture Test</h1>
      <ImageCapture onImageReady={handleImageReady} />
    </div>
  )
}

export default App
