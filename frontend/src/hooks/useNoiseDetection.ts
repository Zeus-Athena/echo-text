/**
 * useNoiseDetection Hook
 * Detect environment noise level and provide threshold recommendations
 */
import { useState, useRef, useCallback } from 'react'

interface UseNoiseDetectionOptions {
    sampleDuration?: number // Duration to sample in ms (default: 3000)
}

interface UseNoiseDetectionReturn {
    isDetecting: boolean
    detectedThreshold: number | null
    detectNoise: () => Promise<number>
    error: string | null
}

// Map RMS value (0-60) to user-facing threshold (0-100)
// Using inverse of the formula in useRealtimeSTT: actualThreshold = Math.pow(threshold / 100, 1.5) * 60
// So: threshold = Math.pow(actualThreshold / 60, 1/1.5) * 100
function rmsToThreshold(rms: number): number {
    // Add some margin above the detected noise floor
    const marginRms = rms * 1.3 + 2 // 30% margin + base offset
    const clampedRms = Math.min(60, Math.max(0, marginRms))
    const threshold = Math.pow(clampedRms / 60, 1 / 1.5) * 100
    return Math.round(Math.min(100, Math.max(0, threshold)))
}

export function useNoiseDetection(options: UseNoiseDetectionOptions = {}): UseNoiseDetectionReturn {
    const { sampleDuration = 3000 } = options

    const [isDetecting, setIsDetecting] = useState(false)
    const [detectedThreshold, setDetectedThreshold] = useState<number | null>(null)
    const [error, setError] = useState<string | null>(null)

    const streamRef = useRef<MediaStream | null>(null)
    const audioContextRef = useRef<AudioContext | null>(null)

    const detectNoise = useCallback(async (): Promise<number> => {
        setIsDetecting(true)
        setError(null)

        try {
            // Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: false, // Disable noise suppression to get true noise level
                }
            })
            streamRef.current = stream

            // Setup AudioContext and Analyser
            const audioContext = new AudioContext()
            const analyser = audioContext.createAnalyser()
            const source = audioContext.createMediaStreamSource(stream)
            source.connect(analyser)
            analyser.fftSize = 256

            audioContextRef.current = audioContext

            // Collect RMS samples over the duration
            const samples: number[] = []
            const sampleInterval = 50 // ms
            const numSamples = Math.floor(sampleDuration / sampleInterval)

            await new Promise<void>((resolve) => {
                let count = 0
                const interval = setInterval(() => {
                    const dataArray = new Uint8Array(analyser.frequencyBinCount)
                    analyser.getByteTimeDomainData(dataArray)

                    // Calculate RMS
                    let sum = 0
                    for (let i = 0; i < dataArray.length; i++) {
                        const x = dataArray[i] - 128
                        sum += x * x
                    }
                    const rms = Math.sqrt(sum / dataArray.length)
                    samples.push(rms)

                    count++
                    if (count >= numSamples) {
                        clearInterval(interval)
                        resolve()
                    }
                }, sampleInterval)
            })

            // Cleanup
            source.disconnect()
            audioContext.close()
            stream.getTracks().forEach(track => track.stop())
            streamRef.current = null
            audioContextRef.current = null

            // Calculate average RMS (excluding top 10% outliers - might be speech)
            const sortedSamples = [...samples].sort((a, b) => a - b)
            const trimCount = Math.floor(sortedSamples.length * 0.1)
            const trimmedSamples = sortedSamples.slice(0, sortedSamples.length - trimCount)
            const avgRms = trimmedSamples.reduce((a, b) => a + b, 0) / trimmedSamples.length

            // Convert to threshold
            const threshold = rmsToThreshold(avgRms)

            console.log(`[NoiseDetection] Average RMS: ${avgRms.toFixed(2)}, Recommended threshold: ${threshold}`)

            setDetectedThreshold(threshold)
            setIsDetecting(false)
            return threshold

        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : '检测失败'
            setError(errorMsg)
            setIsDetecting(false)

            // Cleanup on error
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop())
                streamRef.current = null
            }
            if (audioContextRef.current) {
                audioContextRef.current.close()
                audioContextRef.current = null
            }

            throw new Error(errorMsg)
        }
    }, [sampleDuration])

    return {
        isDetecting,
        detectedThreshold,
        detectNoise,
        error
    }
}
