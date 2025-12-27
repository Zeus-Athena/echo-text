/**
 * PlaybackWaveform Component
 * Audio playback waveform visualization using wavesurfer.js
 * For use in recording detail page audio player
 */
import { useRef, useEffect, useState } from 'react'

// Note: Requires wavesurfer.js to be installed
// npm install wavesurfer.js

interface PlaybackWaveformProps {
    /** Audio source URL */
    audioUrl: string
    /** Whether audio is playing */
    isPlaying: boolean
    /** Current playback time in seconds */
    currentTime?: number
    /** Callback when user seeks by clicking waveform */
    onSeek?: (time: number) => void
    /** Callback when waveform is ready */
    onReady?: (duration: number) => void
    /** Waveform color */
    waveColor?: string
    /** Progress color (played portion) */
    progressColor?: string
    /** Cursor color */
    cursorColor?: string
    /** Height in pixels */
    height?: number
    /** Volume (0-1) */
    volume?: number
}

export default function PlaybackWaveform({
    audioUrl,
    isPlaying,
    currentTime,
    onSeek,
    onReady,
    waveColor = '#94a3b8', // gray-400
    progressColor = '#a855f7', // brand-500
    cursorColor = '#c084fc', // brand-400
    height = 80,
    volume = 1,
}: PlaybackWaveformProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const wavesurferRef = useRef<any>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Store callbacks in refs to avoid re-initializing wavesurfer
    const onSeekRef = useRef(onSeek)
    const onReadyRef = useRef(onReady)

    useEffect(() => {
        onSeekRef.current = onSeek
    }, [onSeek])

    useEffect(() => {
        onReadyRef.current = onReady
    }, [onReady])

    useEffect(() => {
        if (!containerRef.current || !audioUrl) return

        let isMounted = true

        const initWavesurfer = async () => {
            try {
                // Dynamic import to avoid SSR issues
                const WaveSurfer = (await import('wavesurfer.js')).default

                if (!isMounted || !containerRef.current) return

                // Destroy existing instance
                if (wavesurferRef.current) {
                    wavesurferRef.current.destroy()
                }

                const wavesurfer = WaveSurfer.create({
                    container: containerRef.current,
                    waveColor,
                    progressColor,
                    cursorColor,
                    cursorWidth: 2,
                    height,
                    barWidth: 2,
                    barGap: 1,
                    barRadius: 2,
                    normalize: true,
                    backend: 'WebAudio',
                })

                wavesurfer.on('ready', () => {
                    if (isMounted) {
                        setIsLoading(false)
                        onReadyRef.current?.(wavesurfer.getDuration())
                    }
                })

                wavesurfer.on('error', (err: Error) => {
                    if (isMounted) {
                        setError(err.message)
                        setIsLoading(false)
                    }
                })

                wavesurfer.on('interaction', () => {
                    if (isMounted && onSeekRef.current) {
                        onSeekRef.current(wavesurfer.getCurrentTime())
                    }
                })

                // Load audio
                await wavesurfer.load(audioUrl)

                wavesurferRef.current = wavesurfer
            } catch (err) {
                // wavesurfer.js might not be installed
                if (isMounted) {
                    setError('波形库未安装，请运行: npm install wavesurfer.js')
                    setIsLoading(false)
                }
            }
        }

        initWavesurfer()

        return () => {
            isMounted = false
            if (wavesurferRef.current) {
                wavesurferRef.current.destroy()
                wavesurferRef.current = null
            }
        }
    }, [audioUrl, waveColor, progressColor, cursorColor, height])

    // Handle play/pause
    useEffect(() => {
        if (!wavesurferRef.current) return

        if (isPlaying) {
            wavesurferRef.current.play()
        } else {
            wavesurferRef.current.pause()
        }
    }, [isPlaying])

    // Handle volume change
    useEffect(() => {
        if (!wavesurferRef.current) return
        wavesurferRef.current.setVolume(volume)
    }, [volume])

    // Handle seek from external control
    useEffect(() => {
        if (!wavesurferRef.current || currentTime === undefined) return

        const wavesurferTime = wavesurferRef.current.getCurrentTime()
        // Only seek if there's a significant difference (avoid loops)
        if (Math.abs(wavesurferTime - currentTime) > 0.5) {
            wavesurferRef.current.setTime(currentTime)
        }
    }, [currentTime])

    if (error) {
        return (
            <div
                className="flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 rounded-lg bg-gray-100 dark:bg-gray-800"
                style={{ height }}
            >
                {error}
            </div>
        )
    }

    return (
        <div className="relative">
            {isLoading && (
                <div
                    className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg"
                    style={{ height }}
                >
                    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
                            <circle
                                className="opacity-25"
                                cx="12" cy="12" r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                        </svg>
                        加载波形...
                    </div>
                </div>
            )}
            <div
                ref={containerRef}
                className="w-full rounded-lg overflow-hidden"
                style={{ minHeight: height, opacity: isLoading ? 0 : 1 }}
            />
        </div>
    )
}
