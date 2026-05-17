import { useState, useRef, useEffect, startTransition, type CSSProperties } from "react"
import { addPropertyControls, useIsStaticRenderer } from "framer"
import { motion, AnimatePresence } from "framer-motion"

const API_URL = "https://chicfinder-production.up.railway.app"

interface Item {
    id: string
    name: string
    category: string
    image_url: string
    price: number | string | null
    brand: string
    product_url?: string
}

type Phase = "choose" | "camera" | "loading" | "results" | "error"

interface RecommendPageProps {
    style?: CSSProperties
}

async function callRecommend(blob: Blob): Promise<Item[]> {
    const formData = new FormData()
    formData.append("file", blob, "photo.jpg")
    const res = await fetch(`${API_URL}/api/v1/recommend`, {
        method: "POST",
        body: formData,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    return data.recommendations?.[0]?.recommendations ?? []
}

function ProductCard({ item, delay, onClick }: { item: Item; delay: number; onClick: () => void }) {
    const price =
        item.price != null && item.price !== "N/A"
            ? `LE ${typeof item.price === "number" ? item.price.toLocaleString("en-EG") : item.price}`
            : null

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ delay, type: "spring", stiffness: 300, damping: 24 }}
            style={{
                display: "flex",
                flexDirection: "column",
                borderRadius: 16,
                overflow: "hidden",
                backgroundColor: "#f5f5f0",
                cursor: "pointer",
            }}
            whileHover={{ scale: 1.03, boxShadow: "0 8px 24px rgba(0,0,0,0.1)" }}
            whileTap={{ scale: 0.97 }}
            onClick={onClick}
        >
            <div style={{ position: "relative", aspectRatio: "4/5", overflow: "hidden" }}>
                {item.image_url ? (
                    <motion.img
                        src={item.image_url}
                        alt={item.name || item.category}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        whileHover={{ scale: 1.08 }}
                        transition={{ duration: 0.4 }}
                    />
                ) : (
                    <div
                        style={{
                            width: "100%",
                            height: "100%",
                            backgroundColor: "#e8e8e0",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 40,
                            opacity: 0.3,
                        }}
                    >
                        Fashion
                    </div>
                )}
            </div>
            <div style={{ padding: "12px 14px 16px" }}>
                {item.brand && (
                    <p
                        style={{
                            margin: 0,
                            fontSize: 10,
                            color: "#888",
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                            fontWeight: 600,
                        }}
                    >
                        {item.brand}
                    </p>
                )}
                <p
                    style={{
                        margin: "4px 0",
                        fontSize: 13,
                        fontWeight: 700,
                        color: "#111",
                        overflow: "hidden",
                        display: "-webkit-box",
                        WebkitBoxOrient: "vertical",
                        WebkitLineClamp: 2,
                    }}
                >
                    {item.name || item.category}
                </p>
                {price && (
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: "#111" }}>{price}</p>
                )}
            </div>
        </motion.div>
    )
}

function ProductModal({ item, onClose }: { item: Item; onClose: () => void }) {
    const [activeImg, setActiveImg] = useState(0)
    const imgs = item.image_url ? [item.image_url] : []
    const price =
        item.price != null && item.price !== "N/A"
            ? `LE ${typeof item.price === "number" ? item.price.toLocaleString("en-EG") : item.price}`
            : null

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                backgroundColor: "rgba(0,0,0,0.6)",
                backdropFilter: "blur(6px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 24,
            }}
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.92, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.92, y: 20 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                style={{
                    backgroundColor: "#fff",
                    borderRadius: 24,
                    width: "100%",
                    maxWidth: 640,
                    maxHeight: "90vh",
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <div style={{ position: "relative", height: 360, backgroundColor: "#f5f5f0", flexShrink: 0 }}>
                    {imgs[activeImg] ? (
                        <img
                            src={imgs[activeImg]}
                            alt={item.name || item.category}
                            style={{ width: "100%", height: "100%", objectFit: "contain" }}
                        />
                    ) : (
                        <div
                            style={{
                                width: "100%",
                                height: "100%",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: 64,
                                opacity: 0.2,
                            }}
                        >
                            No Image
                        </div>
                    )}
                    <button
                        onClick={onClose}
                        style={{
                            position: "absolute",
                            top: 16,
                            right: 16,
                            background: "rgba(0,0,0,0.5)",
                            border: "none",
                            borderRadius: "50%",
                            width: 36,
                            height: 36,
                            cursor: "pointer",
                            color: "#fff",
                            fontSize: 16,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                        }}
                    >
                        x
                    </button>
                </div>
                {imgs.length > 1 && (
                    <div style={{ display: "flex", gap: 8, padding: "12px 20px", overflowX: "auto", flexShrink: 0 }}>
                        {imgs.map((src, i) => (
                            <motion.button
                                key={i}
                                onClick={() => startTransition(() => setActiveImg(i))}
                                style={{
                                    flex: "none",
                                    width: 56,
                                    height: 56,
                                    borderRadius: 10,
                                    overflow: "hidden",
                                    border: activeImg === i ? "2px solid #111" : "2px solid transparent",
                                    cursor: "pointer",
                                    padding: 0,
                                }}
                                whileHover={{ scale: 1.06 }}
                            >
                                <img src={src} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                            </motion.button>
                        ))}
                    </div>
                )}
                <div style={{ padding: "20px 24px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
                    {item.brand && (
                        <p
                            style={{
                                margin: 0,
                                fontSize: 11,
                                color: "#888",
                                textTransform: "uppercase",
                                letterSpacing: "0.08em",
                                fontWeight: 600,
                            }}
                        >
                            {item.brand}
                        </p>
                    )}
                    <p style={{ margin: 0, fontSize: 20, fontWeight: 800, color: "#111", lineHeight: 1.3 }}>
                        {item.name || item.category}
                    </p>
                    {price && (
                        <p style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "#111" }}>{price}</p>
                    )}
                    {item.product_url ? (
                        <motion.a
                            href={item.product_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                                display: "block",
                                backgroundColor: "#111",
                                color: "#fff",
                                textAlign: "center",
                                padding: "14px 24px",
                                borderRadius: 32,
                                fontSize: 13,
                                fontWeight: 800,
                                letterSpacing: "0.1em",
                                textTransform: "uppercase",
                                textDecoration: "none",
                                marginTop: 4,
                            }}
                            whileHover={{ scale: 1.02, backgroundColor: "#333" }}
                            whileTap={{ scale: 0.98 }}
                        >
                            Shop Now
                        </motion.a>
                    ) : (
                        <div
                            style={{
                                backgroundColor: "#e5e5e5",
                                color: "#aaa",
                                textAlign: "center",
                                padding: "14px 24px",
                                borderRadius: 32,
                                fontSize: 13,
                                fontWeight: 800,
                                letterSpacing: "0.1em",
                                textTransform: "uppercase",
                            }}
                        >
                            Currently Unavailable
                        </div>
                    )}
                </div>
            </motion.div>
        </motion.div>
    )
}

/**
 * @framerIntrinsicWidth 1200
 * @framerIntrinsicHeight 800
 * @framerSupportedLayoutWidth any
 * @framerSupportedLayoutHeight any
 */
export default function RecommendPage(props: RecommendPageProps) {
    const { style } = props
    const isStatic = useIsStaticRenderer()

    const [phase, setPhase] = useState<Phase>("choose")
    const [items, setItems] = useState<Item[]>([])
    const [errorMsg, setErrorMsg] = useState("")
    const [selectedItem, setSelectedItem] = useState<Item | null>(null)
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const videoRef = useRef<HTMLVideoElement>(null)
    const streamRef = useRef<MediaStream | null>(null)

    useEffect(() => {
        if (isStatic || phase !== "camera") return
        let active = true
        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: "environment" }, audio: false })
            .then((stream) => {
                if (!active) {
                    stream.getTracks().forEach((t) => t.stop())
                    return
                }
                streamRef.current = stream
                if (videoRef.current) videoRef.current.srcObject = stream
            })
            .catch(() => {
                if (!active) return
                setErrorMsg("Camera access denied. Please allow camera permissions and try again.")
                setPhase("error")
            })
        return () => {
            active = false
            streamRef.current?.getTracks().forEach((t) => t.stop())
            streamRef.current = null
        }
    }, [phase, isStatic])

    const stopCamera = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
    }

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return
        e.target.value = ""
        setPreviewUrl(URL.createObjectURL(file))
        await runRecommend(file)
    }

    const handleCapture = async () => {
        const video = videoRef.current
        if (!video) return
        const canvas = document.createElement("canvas")
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        canvas.getContext("2d")!.drawImage(video, 0, 0)
        stopCamera()
        canvas.toBlob(async (blob) => {
            if (!blob) {
                setErrorMsg("Failed to capture photo.")
                setPhase("error")
                return
            }
            setPreviewUrl(URL.createObjectURL(blob))
            await runRecommend(blob)
        }, "image/jpeg", 0.92)
    }

    const runRecommend = async (file: File | Blob) => {
        setPhase("loading")
        try {
            const results = await callRecommend(file)
            setItems(results)
            setPhase("results")
        } catch (err) {
            console.error("[ChicFinder] recommend failed:", err)
            setErrorMsg("Something went wrong. Please try again.")
            setPhase("error")
        }
    }

    const reset = () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl)
        setPreviewUrl(null)
        setItems([])
        setPhase("choose")
    }

    const baseContainer: CSSProperties = {
        display: "flex",
        flexDirection: "column",
        paddingTop: 100,
        paddingBottom: 60,
        paddingLeft: 40,
        paddingRight: 40,
        maxWidth: 1400,
        margin: "0 auto",
        boxSizing: "border-box",
        fontFamily: "inherit",
        width: "100%",
        ...style,
    }

    const centeredContainer: CSSProperties = {
        ...baseContainer,
        alignItems: "center",
        justifyContent: "center",
        minHeight: 700,
        gap: 0,
    }

    if (phase === "choose") {
        return (
            <div style={centeredContainer}>
                <style>{`
                    .uv-btn {
                        padding: 15px 25px;
                        border: unset;
                        border-radius: 15px;
                        color: #212121;
                        z-index: 1;
                        background: #e8e8e8;
                        position: relative;
                        font-weight: 1000;
                        font-size: 17px;
                        -webkit-box-shadow: 4px 8px 19px -3px rgba(0,0,0,0.27);
                        box-shadow: 4px 8px 19px -3px rgba(0,0,0,0.27);
                        transition: all 250ms;
                        overflow: hidden;
                        cursor: pointer;
                    }
                    .uv-btn::before {
                        content: "";
                        position: absolute;
                        top: 0; left: 0;
                        height: 100%; width: 0;
                        border-radius: 15px;
                        background-color: #212121;
                        z-index: -1;
                        -webkit-box-shadow: 4px 8px 19px -3px rgba(0,0,0,0.27);
                        box-shadow: 4px 8px 19px -3px rgba(0,0,0,0.27);
                        transition: all 250ms;
                    }
                    .uv-btn:hover { color: #e8e8e8; }
                    .uv-btn:hover::before { width: 100%; }
                `}</style>
                <h2 style={{
                    fontFamily: "Anton, sans-serif",
                    fontSize: 64,
                    fontWeight: 400,
                    color: "#111",
                    margin: 0,
                    textAlign: "center",
                    textTransform: "uppercase",
                    lineHeight: 0.9,
                    letterSpacing: 0,
                }}>
                    Find Your Match
                </h2>
                <p style={{ fontSize: 16, color: "#444", textAlign: "center", maxWidth: 340, margin: "20px 0 40px", lineHeight: 1.5 }}>
                    Upload a fashion photo or take one now — we'll find the closest items from Egyptian stores.
                </p>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
                    <motion.button
                        className="uv-btn"
                        onClick={() => fileInputRef.current?.click()}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                    >
                        Upload Photo
                    </motion.button>
                    <motion.button
                        className="uv-btn"
                        onClick={() => setPhase("camera")}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                    >
                        Camera Capture
                    </motion.button>
                </div>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp"
                    style={{ display: "none" }}
                    onChange={handleFileChange}
                />
            </div>
        )
    }

    if (phase === "camera") {
        return (
            <div style={{ width: "100%", backgroundColor: "#000", display: "flex", flexDirection: "column", fontFamily: "inherit", minHeight: 500 }}>
                <video ref={videoRef} autoPlay playsInline muted style={{ width: "100%", maxHeight: 480, objectFit: "cover", display: "block" }} />
                <div style={{ display: "flex", gap: 16, padding: "20px 24px", justifyContent: "center" }}>
                    <button
                        onClick={() => { stopCamera(); setPhase("choose") }}
                        style={{ padding: "12px 28px", borderRadius: 32, border: "2px solid #fff", backgroundColor: "transparent", color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: 14 }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCapture}
                        style={{ padding: "12px 36px", borderRadius: 32, border: "none", backgroundColor: "#fff", color: "#111", cursor: "pointer", fontWeight: 700, fontSize: 15 }}
                    >
                        Capture
                    </button>
                </div>
            </div>
        )
    }

    if (phase === "loading") {
        return (
            <div style={centeredContainer}>
                {previewUrl && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        style={{ position: "relative", marginBottom: 36 }}
                    >
                        <img
                            src={previewUrl}
                            alt="Your photo"
                            style={{
                                width: 210,
                                height: 210,
                                objectFit: "cover",
                                borderRadius: 26,
                                boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
                                display: "block",
                            }}
                        />
                        <motion.div
                            animate={{ opacity: [0.3, 0.7, 0.3] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            style={{ position: "absolute", inset: 0, borderRadius: 20, border: "3px solid #111" }}
                        />
                    </motion.div>
                )}
                <div style={{ width: 48, height: 48, border: "4px solid #eee", borderTop: "4px solid #111", borderRadius: "50%", animation: "spin 0.9s linear infinite", marginBottom: 20 }} />
                <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
                <p style={{ fontSize: 16, fontWeight: 600, color: "#111", margin: 0 }}>Analyzing outfit...</p>
                <p style={{ fontSize: 13, color: "#888", marginTop: 4 }}>This can take up to a minute</p>
            </div>
        )
    }

    if (phase === "error") {
        return (
            <div style={centeredContainer}>
                <p style={{ fontSize: 16, color: "#e53e3e", fontWeight: 600, marginBottom: 16, textAlign: "center" }}>{errorMsg}</p>
                <motion.button
                    onClick={reset}
                    style={{ padding: "10px 28px", borderRadius: 32, border: "none", backgroundColor: "#111", color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: 14 }}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                >
                    Try Again
                </motion.button>
            </div>
        )
    }

    return (
        <div style={{ ...baseContainer, gap: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111", margin: 0 }}>Your Matches</h2>
                <motion.button
                    onClick={reset}
                    style={{ padding: "8px 20px", borderRadius: 32, border: "2px solid #111", backgroundColor: "transparent", color: "#111", cursor: "pointer", fontWeight: 600, fontSize: 13 }}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                >
                    Search Again
                </motion.button>
            </div>
            {previewUrl && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, padding: "4px 0 8px" }}>
                    <img
                        src={previewUrl}
                        alt="Your photo"
                        style={{
                            width: 160,
                            height: 160,
                            objectFit: "cover",
                            borderRadius: 24,
                            boxShadow: "0 4px 12px rgba(0,0,0,0.12)",
                            flexShrink: 0,
                        }}
                    />
                    <div>
                        <p style={{ margin: 0, fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Your photo</p>
                        <p style={{ margin: "2px 0 0", fontSize: 13, color: "#555" }}>Showing closest matches</p>
                    </div>
                </div>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 20, width: "100%" }}>
                <AnimatePresence>
                    {items.map((item, i) => (
                        <ProductCard key={item.id} item={item} delay={i * 0.06} onClick={() => setSelectedItem(item)} />
                    ))}
                </AnimatePresence>
            </div>
            <AnimatePresence>
                {selectedItem && <ProductModal item={selectedItem} onClose={() => setSelectedItem(null)} />}
            </AnimatePresence>
        </div>
    )
}

addPropertyControls(RecommendPage, {})
