import { addPropertyControls } from "framer"
import { useRef, useState, useEffect } from "react"

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

function ProductCard({ item }: { item: Item }) {
    const price =
        item.price != null && item.price !== "N/A"
            ? `EGP ${typeof item.price === "number" ? item.price.toLocaleString() : item.price}`
            : null

    return (
        <div
            style={{
                backgroundColor: "#fff",
                borderRadius: 12,
                overflow: "hidden",
                boxShadow: "0 1px 6px rgba(0,0,0,0.08)",
                display: "flex",
                flexDirection: "column",
            }}
        >
            <img
                src={item.image_url}
                alt={item.name}
                style={{
                    width: "100%",
                    aspectRatio: "3/4",
                    objectFit: "cover",
                    display: "block",
                }}
            />
            <div
                style={{
                    padding: "10px 12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    flexGrow: 1,
                }}
            >
                {item.name && (
                    <div
                        style={{
                            fontWeight: 700,
                            fontSize: 13,
                            lineHeight: 1.3,
                            color: "#111",
                        }}
                    >
                        {item.name}
                    </div>
                )}
                <div style={{ fontSize: 12, color: "#888" }}>
                    {[item.brand, item.category].filter(Boolean).join(" · ")}
                </div>
                {price && (
                    <div
                        style={{
                            fontWeight: 600,
                            fontSize: 13,
                            color: "#111",
                            marginTop: 2,
                        }}
                    >
                        {price}
                    </div>
                )}
                {item.product_url && (
                    <a
                        href={item.product_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        style={{
                            display: "block",
                            marginTop: "auto",
                            paddingTop: 10,
                            textAlign: "center",
                            backgroundColor: "#111",
                            color: "#fff",
                            borderRadius: 8,
                            padding: "8px 0",
                            fontSize: 12,
                            fontWeight: 600,
                            textDecoration: "none",
                        }}
                    >
                        View Product
                    </a>
                )}
            </div>
        </div>
    )
}

export function RecommendPage({ style }: { style?: React.CSSProperties }) {
    const [phase, setPhase] = useState<Phase>("choose")
    const [items, setItems] = useState<Item[]>([])
    const [errorMsg, setErrorMsg] = useState("")
    const fileInputRef = useRef<HTMLInputElement>(null)
    const videoRef = useRef<HTMLVideoElement>(null)
    const streamRef = useRef<MediaStream | null>(null)

    useEffect(() => {
        if (phase !== "camera") return
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
                setErrorMsg(
                    "Camera access denied. Please allow camera permissions and try again."
                )
                setPhase("error")
            })
        return () => {
            active = false
            streamRef.current?.getTracks().forEach((t) => t.stop())
            streamRef.current = null
        }
    }, [phase])

    const stopCamera = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
    }

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return
        e.target.value = ""
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
        canvas.toBlob(
            async (blob) => {
                if (!blob) {
                    setErrorMsg("Failed to capture photo.")
                    setPhase("error")
                    return
                }
                await runRecommend(blob)
            },
            "image/jpeg",
            0.92
        )
    }

    const runRecommend = async (file: File | Blob) => {
        setPhase("loading")
        try {
            const results = await callRecommend(file)
            setItems(results)
            setPhase("results")
        } catch {
            setErrorMsg("Something went wrong. Please try again.")
            setPhase("error")
        }
    }

    const reset = () => {
        setItems([])
        setPhase("choose")
    }

    const containerStyle: React.CSSProperties = {
        width: "100%",
        minHeight: 400,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "inherit",
        padding: "40px 24px",
        boxSizing: "border-box",
        ...style,
    }

    // ── CHOOSE ──────────────────────────────────────────────────
    if (phase === "choose") {
        return (
            <div style={containerStyle}>
                <h2
                    style={{
                        fontSize: 24,
                        fontWeight: 700,
                        color: "#111",
                        marginBottom: 8,
                        textAlign: "center",
                    }}
                >
                    Find Your Match
                </h2>
                <p
                    style={{
                        fontSize: 14,
                        color: "#666",
                        marginBottom: 40,
                        textAlign: "center",
                        maxWidth: 320,
                    }}
                >
                    Upload a fashion photo or take one now — we'll find the closest
                    items from Egyptian stores.
                </p>
                <div
                    style={{
                        display: "flex",
                        gap: 16,
                        flexWrap: "wrap",
                        justifyContent: "center",
                    }}
                >
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: 10,
                            padding: "28px 36px",
                            borderRadius: 16,
                            border: "2px solid #111",
                            backgroundColor: "#111",
                            color: "#fff",
                            cursor: "pointer",
                            minWidth: 140,
                        }}
                    >
                        <span style={{ fontSize: 32 }}>🖼️</span>
                        <span style={{ fontWeight: 600, fontSize: 15 }}>Upload Photo</span>
                        <span style={{ fontSize: 12, color: "#aaa" }}>JPG, PNG or WEBP</span>
                    </button>
                    <button
                        onClick={() => setPhase("camera")}
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: 10,
                            padding: "28px 36px",
                            borderRadius: 16,
                            border: "2px solid #111",
                            backgroundColor: "#fff",
                            color: "#111",
                            cursor: "pointer",
                            minWidth: 140,
                        }}
                    >
                        <span style={{ fontSize: 32 }}>📷</span>
                        <span style={{ fontWeight: 600, fontSize: 15 }}>Camera Capture</span>
                        <span style={{ fontSize: 12, color: "#888" }}>Take a photo now</span>
                    </button>
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

    // ── CAMERA ──────────────────────────────────────────────────
    if (phase === "camera") {
        return (
            <div
                style={{
                    ...containerStyle,
                    padding: 0,
                    backgroundColor: "#000",
                    minHeight: 500,
                }}
            >
                <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    style={{
                        width: "100%",
                        maxHeight: 480,
                        objectFit: "cover",
                        display: "block",
                    }}
                />
                <div
                    style={{
                        display: "flex",
                        gap: 16,
                        padding: "20px 24px",
                        width: "100%",
                        boxSizing: "border-box",
                        justifyContent: "center",
                    }}
                >
                    <button
                        onClick={() => {
                            stopCamera()
                            setPhase("choose")
                        }}
                        style={{
                            padding: "12px 28px",
                            borderRadius: 10,
                            border: "2px solid #fff",
                            backgroundColor: "transparent",
                            color: "#fff",
                            cursor: "pointer",
                            fontWeight: 600,
                            fontSize: 14,
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCapture}
                        style={{
                            padding: "12px 36px",
                            borderRadius: 10,
                            border: "none",
                            backgroundColor: "#fff",
                            color: "#111",
                            cursor: "pointer",
                            fontWeight: 700,
                            fontSize: 15,
                        }}
                    >
                        Capture
                    </button>
                </div>
            </div>
        )
    }

    // ── LOADING ──────────────────────────────────────────────────
    if (phase === "loading") {
        return (
            <div style={containerStyle}>
                <div
                    style={{
                        width: 48,
                        height: 48,
                        border: "4px solid #eee",
                        borderTop: "4px solid #111",
                        borderRadius: "50%",
                        animation: "spin 0.9s linear infinite",
                        marginBottom: 20,
                    }}
                />
                <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
                <p style={{ fontSize: 16, fontWeight: 600, color: "#111" }}>
                    Analyzing outfit...
                </p>
                <p style={{ fontSize: 13, color: "#888", marginTop: 4 }}>
                    This takes a few seconds
                </p>
            </div>
        )
    }

    // ── ERROR ────────────────────────────────────────────────────
    if (phase === "error") {
        return (
            <div style={containerStyle}>
                <p
                    style={{
                        fontSize: 16,
                        color: "#e53e3e",
                        fontWeight: 600,
                        marginBottom: 16,
                        textAlign: "center",
                    }}
                >
                    {errorMsg}
                </p>
                <button
                    onClick={reset}
                    style={{
                        padding: "10px 28px",
                        borderRadius: 10,
                        border: "none",
                        backgroundColor: "#111",
                        color: "#fff",
                        cursor: "pointer",
                        fontWeight: 600,
                        fontSize: 14,
                    }}
                >
                    Try Again
                </button>
            </div>
        )
    }

    // ── RESULTS ──────────────────────────────────────────────────
    return (
        <div style={{ ...style, width: "100%", fontFamily: "inherit" }}>
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "24px 16px 16px",
                }}
            >
                <h2
                    style={{
                        fontSize: 20,
                        fontWeight: 700,
                        color: "#111",
                        margin: 0,
                    }}
                >
                    Your Matches
                </h2>
                <button
                    onClick={reset}
                    style={{
                        padding: "8px 18px",
                        borderRadius: 8,
                        border: "2px solid #111",
                        backgroundColor: "transparent",
                        color: "#111",
                        cursor: "pointer",
                        fontWeight: 600,
                        fontSize: 13,
                    }}
                >
                    Search Again
                </button>
            </div>
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                    gap: 16,
                    padding: "0 16px 32px",
                    width: "100%",
                    boxSizing: "border-box",
                }}
            >
                {items.map((item) => (
                    <ProductCard key={item.id} item={item} />
                ))}
            </div>
        </div>
    )
}

addPropertyControls(RecommendPage, {})
