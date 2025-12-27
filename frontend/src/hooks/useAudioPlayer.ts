/**
 * useAudioPlayer Hook
 * 音频播放器逻辑抽取
 */
import { useState, useRef, useEffect, useCallback } from 'react'

interface UseAudioPlayerOptions {
    recordingId?: string
    audioSize?: number
    s3Key?: string
}

interface UseAudioPlayerReturn {
    // Refs
    audioRef: React.RefObject<HTMLAudioElement>

    // State
    isPlaying: boolean
    currentTime: number
    duration: number
    volume: number
    playbackSpeed: number
    audioError: string | null
    audioBlobUrl: string | null
    isLoading: boolean

    // Actions
    togglePlay: () => void
    setVolume: (vol: number) => void
    setPlaybackSpeed: (speed: number) => void
    skipTime: (seconds: number) => void
    seekTo: (time: number) => void
    formatTime: (seconds: number) => string
}

export function useAudioPlayer({
    recordingId,
    audioSize,
    s3Key
}: UseAudioPlayerOptions): UseAudioPlayerReturn {
    const audioRef = useRef<HTMLAudioElement>(null)

    // State
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [volume, setVolumeState] = useState(1)
    const [playbackSpeed, setPlaybackSpeedState] = useState(1)
    const [audioError, setAudioError] = useState<string | null>(null)
    const [audioBlobUrl, setAudioBlobUrl] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)

    // Check if audio is available
    const hasAudio = !!(audioSize || s3Key)

    // Fetch audio with authentication and create blob URL
    useEffect(() => {
        let mounted = true
        let blobUrl: string | null = null

        const fetchAudio = async () => {
            if (!recordingId || !hasAudio) return

            setIsLoading(true)
            setAudioError(null)

            try {
                // Standard relative path strategy
                const token = localStorage.getItem('access_token')
                const audioResponse = await fetch(`/api/v1/recordings/${recordingId}/audio`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })

                if (!audioResponse.ok) {
                    throw new Error(`HTTP ${audioResponse.status}`)
                }

                const blob = await audioResponse.blob()
                blobUrl = URL.createObjectURL(blob)

                if (mounted) {
                    setAudioBlobUrl(blobUrl)
                }
            } catch (error) {
                console.error('Failed to fetch audio:', error)
                if (mounted) {
                    setAudioError('音频加载失败')
                }
            } finally {
                if (mounted) {
                    setIsLoading(false)
                }
            }
        }

        fetchAudio()

        // Cleanup blob URL on unmount
        return () => {
            mounted = false
            if (blobUrl) {
                URL.revokeObjectURL(blobUrl)
            }
        }
    }, [recordingId, hasAudio])

    // Sync volume to audio element
    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.volume = volume
            audioRef.current.muted = volume === 0
        }
    }, [volume])

    // Sync playback speed to audio element
    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.playbackRate = playbackSpeed
        }
    }, [playbackSpeed])

    // Actions
    const togglePlay = useCallback(() => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause()
            } else {
                audioRef.current.play()
            }
            setIsPlaying(!isPlaying)
        }
    }, [isPlaying])

    const setVolume = useCallback((vol: number) => {
        setVolumeState(vol)
    }, [])

    const setPlaybackSpeed = useCallback((speed: number) => {
        setPlaybackSpeedState(speed)
    }, [])

    const skipTime = useCallback((seconds: number) => {
        if (audioRef.current) {
            const newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds))
            audioRef.current.currentTime = newTime
            setCurrentTime(newTime)
        }
    }, [duration])

    const seekTo = useCallback((time: number) => {
        if (audioRef.current) {
            audioRef.current.currentTime = time
            setCurrentTime(time)
        }
    }, [])

    const formatTime = useCallback((seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${String(secs).padStart(2, '0')}`
    }, [])

    // Audio element event handlers - exposed via ref callbacks
    const handleTimeUpdate = useCallback(() => {
        if (audioRef.current) {
            setCurrentTime(audioRef.current.currentTime)
        }
    }, [])

    const handleLoadedMetadata = useCallback(() => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration)
            audioRef.current.volume = volume
            audioRef.current.muted = volume === 0
        }
    }, [volume])

    const handleEnded = useCallback(() => {
        setIsPlaying(false)
    }, [])

    // Attach event listeners to audio element
    useEffect(() => {
        const audio = audioRef.current
        if (!audio) return

        audio.addEventListener('timeupdate', handleTimeUpdate)
        audio.addEventListener('loadedmetadata', handleLoadedMetadata)
        audio.addEventListener('ended', handleEnded)

        return () => {
            audio.removeEventListener('timeupdate', handleTimeUpdate)
            audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
            audio.removeEventListener('ended', handleEnded)
        }
    }, [handleTimeUpdate, handleLoadedMetadata, handleEnded])

    return {
        audioRef,
        isPlaying,
        currentTime,
        duration,
        volume,
        playbackSpeed,
        audioError,
        audioBlobUrl,
        isLoading,
        togglePlay,
        setVolume,
        setPlaybackSpeed,
        skipTime,
        seekTo,
        formatTime
    }
}
