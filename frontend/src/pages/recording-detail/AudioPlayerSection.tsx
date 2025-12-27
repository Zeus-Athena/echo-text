
import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import {
    Play,
    Pause,
    Volume2,
    VolumeX,
    SkipBack,
    SkipForward,
    Loader2
} from 'lucide-react'
import PlaybackWaveform from '@/components/PlaybackWaveform'

interface AudioPlayerSectionProps {
    recording: any
    id: string | undefined
    onTimeUpdate?: (time: number) => void
    onSeek?: (time: number) => void  // 用户点击进度条 seek 时调用
}

export interface AudioPlayerRef {
    currentTime: number
    setCurrentTime: (time: number) => void
    duration: number
    setDuration: (dur: number) => void
    isPlaying: boolean
    setIsPlaying: (playing: boolean) => void
    audioRef: React.RefObject<HTMLAudioElement>
}

export const AudioPlayerSection = forwardRef<AudioPlayerRef, AudioPlayerSectionProps>(({ recording, id, onTimeUpdate, onSeek }, ref) => {
    const audioRef = useRef<HTMLAudioElement>(null)
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [volume, setVolume] = useState(1)
    const [playbackSpeed, setPlaybackSpeed] = useState(1)
    const [audioError, setAudioError] = useState<string | null>(null)
    const [audioBlobUrl, setAudioBlobUrl] = useState<string | null>(null)

    useImperativeHandle(ref, () => ({
        currentTime,
        setCurrentTime: (time: number) => {
            if (audioRef.current) {
                audioRef.current.currentTime = time
            }
            setCurrentTime(time)
        },
        duration,
        setDuration,
        isPlaying,
        setIsPlaying: (playing: boolean) => {
            if (audioRef.current) {
                if (playing) audioRef.current.play()
                else audioRef.current.pause()
            }
            setIsPlaying(playing)
        },
        audioRef
    }))

    useEffect(() => {
        const fetchAudio = async () => {
            if (!id || !recording) return
            const hasAudio = recording.audio_size || recording.s3_key
            if (!hasAudio) return

            try {
                setAudioError(null)
                const token = localStorage.getItem('access_token')
                const baseUrl = (import.meta as any).env?.VITE_API_URL || ''
                const audioResponse = await fetch(`${baseUrl}/api/v1/recordings/${id}/audio`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })

                if (!audioResponse.ok) throw new Error(`HTTP ${audioResponse.status}`)

                const blob = await audioResponse.blob()
                const blobUrl = URL.createObjectURL(blob)
                setAudioBlobUrl(blobUrl)
            } catch (error) {
                console.error('Failed to fetch audio:', error)
                setAudioError('音频加载失败')
            }
        }

        fetchAudio()
        return () => {
            if (audioBlobUrl) URL.revokeObjectURL(audioBlobUrl)
        }
    }, [id, recording])

    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.volume = volume
            audioRef.current.muted = (volume === 0)
        }
    }, [volume])

    const togglePlay = () => {
        if (audioRef.current) {
            if (isPlaying) audioRef.current.pause()
            else audioRef.current.play()
            setIsPlaying(!isPlaying)
        }
    }

    const skipTime = (seconds: number) => {
        if (audioRef.current) {
            const newTime = Math.max(0, Math.min(duration || recording.duration_seconds, audioRef.current.currentTime + seconds))
            audioRef.current.currentTime = newTime
            setCurrentTime(newTime)
        }
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${String(secs).padStart(2, '0')}`
    }

    const hasAudio = recording.audio_size || recording.s3_key

    if (!hasAudio) return null

    return (
        <>
            <audio
                ref={audioRef}
                onTimeUpdate={() => {
                    if (audioRef.current) {
                        setCurrentTime(audioRef.current.currentTime)
                        onTimeUpdate?.(audioRef.current.currentTime)
                    }
                }}
                onLoadedMetadata={() => {
                    if (audioRef.current) {
                        setDuration(audioRef.current.duration)
                        audioRef.current.volume = volume
                        audioRef.current.muted = (volume === 0)
                    }
                }}
                onEnded={() => setIsPlaying(false)}
                src={audioBlobUrl || undefined}
            />

            <div className="card p-4 mb-6">
                {audioError ? (
                    <div className="text-center text-red-500 py-2">{audioError}</div>
                ) : !audioBlobUrl ? (
                    <div className="flex items-center justify-center py-2 text-gray-500">
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                        加载音频中...
                    </div>
                ) : (
                    <div className="flex items-center gap-6">
                        <button
                            onClick={() => skipTime(-5)}
                            className="p-2 text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-full transition-colors shrink-0 border border-transparent hover:border-brand-100/50"
                            title="快退 5 秒"
                        >
                            <SkipBack className="w-5 h-5" />
                        </button>

                        <button
                            onClick={togglePlay}
                            className="w-12 h-12 rounded-full bg-brand-500 text-white flex items-center justify-center hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/20 shrink-0"
                        >
                            {isPlaying ? (
                                <Pause className="w-5 h-5 fill-current" />
                            ) : (
                                <Play className="w-5 h-5 fill-current ml-0.5" />
                            )}
                        </button>

                        <button
                            onClick={() => skipTime(5)}
                            className="p-2 text-gray-400 hover:text-brand-500 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-full transition-colors shrink-0 border border-transparent hover:border-brand-100/50"
                            title="快进 5 秒"
                        >
                            <SkipForward className="w-5 h-5" />
                        </button>

                        <div className="flex-1 flex flex-col justify-center relative group">
                            <PlaybackWaveform
                                key={audioBlobUrl}
                                audioUrl={audioBlobUrl}
                                currentTime={currentTime}
                                isPlaying={isPlaying}
                                volume={volume}
                                onSeek={(time) => {
                                    if (audioRef.current) {
                                        audioRef.current.currentTime = time
                                        setCurrentTime(time)
                                    }
                                    // 通知父组件 seek 发生，以便递增 seekVersion
                                    onSeek?.(time)
                                }}
                                onReady={(dur) => setDuration(dur)}
                                height={50}
                            />
                            <div className="absolute -bottom-4 left-0 right-0 flex justify-between text-[10px] text-gray-400 font-mono pointer-events-none select-none">
                                <span>{formatTime(currentTime)}</span>
                                <span>{formatTime(duration || recording.duration_seconds)}</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                            <span className="text-xs text-gray-400">速度</span>
                            <select
                                value={playbackSpeed}
                                onChange={(e) => {
                                    const speed = Number(e.target.value)
                                    setPlaybackSpeed(speed)
                                    if (audioRef.current) audioRef.current.playbackRate = speed
                                }}
                                className="bg-transparent hover:bg-brand-50 dark:hover:bg-gray-800 rounded pl-2 pr-7 py-0.5 cursor-pointer outline-none text-xs text-brand-700 dark:text-brand-300 border border-brand-100/50 dark:border-brand-800/60 focus:border-brand-300 dark:focus:border-brand-700 h-7 transition-colors"
                            >
                                <option value="0.5">0.5x</option>
                                <option value="1">1.0x</option>
                                <option value="1.25">1.25x</option>
                                <option value="1.5">1.5x</option>
                                <option value="2">2.0x</option>
                            </select>
                        </div>

                        <div className="relative group shrink-0">
                            <button className="p-2 text-gray-400 hover:text-brand-600 dark:hover:text-brand-400 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg transition-colors border border-transparent hover:border-brand-100/50">
                                {volume === 0 ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                            </button>
                            <div className="absolute bottom-full right-0 w-40 pb-2 hidden group-hover:block hover:block">
                                <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-brand-100 dark:border-brand-800 p-3 flex items-center gap-2 h-10">
                                    <div className="relative flex-1 h-4 flex items-center">
                                        <div className="absolute inset-x-0 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full" />
                                        <div className="absolute h-1.5 bg-brand-500 rounded-full transition-all" style={{ width: `${volume * 100}%` }} />
                                        <input
                                            type="range"
                                            min={0}
                                            max={1}
                                            step={0.05}
                                            value={volume}
                                            onChange={(e) => setVolume(parseFloat(e.target.value))}
                                            className="relative w-full h-4 appearance-none bg-transparent cursor-pointer z-10"
                                        />
                                    </div>
                                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 w-8 text-right tabular-nums">
                                        {Math.round(volume * 100)}%
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </>
    )
})
