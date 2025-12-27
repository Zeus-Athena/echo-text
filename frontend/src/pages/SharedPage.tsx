/**
 * SharedPage Component
 * Public page for viewing shared recordings (no login required)
 * Matches UI of RecordingDetailPage but read-only
 */
import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { shareApi } from '@/api/client'
import {
    Play,
    Pause,
    Lock,
    FileText,
    Globe,
    Sparkles,
    Volume2,
    VolumeX,
    SkipBack,
    SkipForward,
    Target,
    Check,
    Copy,
    Loader2
} from 'lucide-react'
import PlaybackWaveform from '@/components/PlaybackWaveform'
import TranscriptCard from '@/components/TranscriptCard'

export default function SharedPage() {
    const { token } = useParams<{ token: string }>()
    const [password, setPassword] = useState('')
    const [submittedPassword, setSubmittedPassword] = useState<string | undefined>()

    // Audio State
    const [isPlaying, setIsPlaying] = useState(false)
    const audioRef = useRef<HTMLAudioElement | null>(null)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [volume, setVolume] = useState(1)
    const [playbackSpeed, setPlaybackSpeed] = useState(1)
    const [audioLoaded, setAudioLoaded] = useState(false)
    const [audioError, setAudioError] = useState<string | null>(null)
    const [seekVersion, setSeekVersion] = useState(0)  // 用于强制触发卡片滚动

    // Prevent UI jumping by ignoring time updates shortly after seek
    const ignoreUpdatesUntil = useRef(0)

    const { data: shared, isLoading, error, refetch } = useQuery({
        queryKey: ['shared', token, submittedPassword],
        queryFn: async () => {
            const res = await shareApi.accessShared(token!, submittedPassword)
            return res.data
        },
        enabled: !!token,
        retry: false,
    })

    const handlePasswordSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        setSubmittedPassword(password)
        refetch()
    }

    // Audio controls
    const togglePlay = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause()
            } else {
                audioRef.current.play().catch(e => {
                    console.error('Audio play error:', e)
                    setAudioError('播放失败，请重试')
                })
            }
            setIsPlaying(!isPlaying)
        }
    }

    // Sync volume to audio element
    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.volume = volume
            audioRef.current.muted = (volume === 0)
        }
    }, [volume])

    const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const vol = parseFloat(e.target.value)
        setVolume(vol)
    }

    const handleSpeedChange = (speed: number) => {
        setPlaybackSpeed(speed)
        if (audioRef.current) {
            audioRef.current.playbackRate = speed
        }
    }

    const skipTime = (seconds: number) => {
        if (audioRef.current) {
            // Block updates for 500ms
            ignoreUpdatesUntil.current = Date.now() + 500

            const newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds))
            audioRef.current.currentTime = newTime
            setCurrentTime(newTime)
        }
    }

    // 点击转录卡片跳转到指定时间并播放
    const handleSeek = (time: number) => {
        // Block updates for 500ms to allow audio engine to settle
        ignoreUpdatesUntil.current = Date.now() + 500

        if (audioRef.current) {
            audioRef.current.currentTime = time
            setCurrentTime(time)
            if (!isPlaying) {
                audioRef.current.play().catch(e => console.error('Play error:', e))
                setIsPlaying(true)
            }
        }
        // 递增 seekVersion 以强制触发卡片滚动
        setSeekVersion(v => v + 1)
    }

    // Format time
    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${String(secs).padStart(2, '0')}`
    }

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text)
    }

    // Loading state
    if (isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    // Password required
    if (error && (error as any)?.response?.status === 401) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
                <div className="card max-w-md w-full p-8">
                    <div className="text-center mb-6">
                        <div className="w-16 h-16 mx-auto bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mb-4">
                            <Lock className="w-8 h-8 text-brand-600" />
                        </div>
                        <h1 className="text-xl font-bold">受密码保护的内容</h1>
                        <p className="text-gray-500 mt-2">请输入密码以访问此分享内容</p>
                    </div>
                    <form onSubmit={handlePasswordSubmit}>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="输入密码"
                            className="input mb-4"
                            autoFocus
                        />
                        <button type="submit" className="btn-primary w-full">
                            访问
                        </button>
                    </form>
                    {submittedPassword && (
                        <p className="text-red-500 text-sm text-center mt-4">密码错误，请重试</p>
                    )}
                </div>
            </div>
        )
    }

    // Expired or error
    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
                <div className="card max-w-md w-full p-8 text-center">
                    <div className="w-16 h-16 mx-auto bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                        <FileText className="w-8 h-8 text-gray-400" />
                    </div>
                    <h1 className="text-xl font-bold">链接已失效</h1>
                    <p className="text-gray-500 mt-2">
                        此分享链接不存在、已过期或已达到最大访问次数
                    </p>
                </div>
            </div>
        )
    }

    if (!shared) return null

    return (
        <div className="h-full flex flex-col pt-4 px-4 lg:px-8 max-w-7xl mx-auto bg-gray-50 dark:bg-gray-950 min-h-screen">
            {/* Audio Element */}
            {shared.has_audio && (
                <audio
                    ref={audioRef}
                    src={shareApi.getShareAudioUrl(token!, submittedPassword)}
                    onTimeUpdate={() => {
                        // Check if we are in the "ignore window" after a seek
                        if (Date.now() < ignoreUpdatesUntil.current) {
                            return
                        }
                        if (audioRef.current) setCurrentTime(audioRef.current.currentTime)
                    }}
                    onLoadedMetadata={() => {
                        if (audioRef.current) {
                            setDuration(audioRef.current.duration)
                            setAudioLoaded(true)
                            audioRef.current.volume = volume
                            audioRef.current.muted = (volume === 0)
                        }
                    }}
                    onEnded={() => setIsPlaying(false)}
                    onError={() => setAudioError('音频加载失败')}
                />
            )}

            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                        {shared.title}
                    </h1>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{new Date(shared.created_at).toLocaleString()}</span>
                        <span>·</span>
                        <span>{Math.floor(shared.duration_seconds / 60)}分{Math.floor(shared.duration_seconds % 60)}秒</span>
                        <span>·</span>
                        <span>{shared.source_lang.toUpperCase()} → {shared.target_lang.toUpperCase()}</span>
                    </div>
                </div>
            </div>

            {/* Audio Player */}
            {shared.has_audio && (
                <div className="card p-4 mb-6">
                    {audioError ? (
                        <div className="text-center text-red-500 py-2">
                            {audioError}
                        </div>
                    ) : (
                        <div className="flex items-center gap-6">
                            {/* 1. Skip Back */}
                            <button
                                onClick={() => skipTime(-5)}
                                className="p-2 text-gray-400 hover:text-brand-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors shrink-0"
                                title="快退 5 秒"
                            >
                                <SkipBack className="w-5 h-5" />
                            </button>

                            {/* 2. Play/Pause */}
                            <button
                                onClick={togglePlay}
                                disabled={!audioLoaded}
                                className="w-12 h-12 rounded-full bg-brand-500 text-white flex items-center justify-center hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/20 shrink-0 disabled:bg-gray-300 disabled:cursor-not-allowed"
                            >
                                {isPlaying ? (
                                    <Pause className="w-5 h-5 fill-current" />
                                ) : (
                                    <Play className="w-5 h-5 fill-current ml-0.5" />
                                )}
                            </button>

                            {/* 3. Skip Forward */}
                            <button
                                onClick={() => skipTime(5)}
                                className="p-2 text-gray-400 hover:text-brand-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors shrink-0"
                                title="快进 5 秒"
                            >
                                <SkipForward className="w-5 h-5" />
                            </button>

                            {/* 4. Waveform */}
                            <div className="flex-1 flex flex-col justify-center relative group">
                                <PlaybackWaveform
                                    audioUrl={shareApi.getShareAudioUrl(token!, submittedPassword)}
                                    currentTime={currentTime}
                                    isPlaying={isPlaying}
                                    volume={volume}
                                    onSeek={(time) => {
                                        if (audioRef.current) {
                                            audioRef.current.currentTime = time
                                            setCurrentTime(time)
                                        }
                                        // 递增 seekVersion 以触发卡片滚动
                                        setSeekVersion(v => v + 1)
                                    }}
                                    onReady={(dur) => setDuration(dur)}
                                    height={50}
                                />
                                <div className="absolute -bottom-4 left-0 right-0 flex justify-between text-[10px] text-gray-400 font-mono pointer-events-none select-none">
                                    <span>{formatTime(currentTime)}</span>
                                    <span>{formatTime(duration || shared.duration_seconds)}</span>
                                </div>
                            </div>

                            {/* 5. Speed */}
                            <div className="flex items-center gap-2 shrink-0">
                                <span className="text-xs text-gray-400">速度</span>
                                <select
                                    value={playbackSpeed}
                                    onChange={(e) => handleSpeedChange(Number(e.target.value))}
                                    className="bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded pl-2 pr-7 py-0.5 cursor-pointer outline-none text-xs text-gray-600 dark:text-gray-300 border border-transparent focus:border-brand-200 dark:focus:border-brand-800 h-7"
                                >
                                    <option value="0.5">0.5x</option>
                                    <option value="1">1.0x</option>
                                    <option value="1.25">1.25x</option>
                                    <option value="1.5">1.5x</option>
                                    <option value="2">2.0x</option>
                                </select>
                            </div>

                            {/* 6. Volume */}
                            <div className="relative group shrink-0">
                                <button
                                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                                >
                                    {volume === 0 ? (
                                        <VolumeX className="w-5 h-5" />
                                    ) : (
                                        <Volume2 className="w-5 h-5" />
                                    )}
                                </button>
                                {/* Clean Horizontal Volume Slider Popup */}
                                <div className="absolute bottom-full right-0 w-40 pb-2 hidden group-hover:block hover:block">
                                    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-100 dark:border-gray-700 p-3 flex items-center gap-2 h-10">
                                        <div className="relative flex-1 h-4 flex items-center">
                                            {/* Track background */}
                                            <div className="absolute inset-x-0 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full" />
                                            {/* Progress fill */}
                                            <div
                                                className="absolute h-1.5 bg-brand-500 rounded-full transition-all"
                                                style={{ width: `${volume * 100}%` }}
                                            />
                                            {/* Slider input */}
                                            <input
                                                type="range"
                                                min={0}
                                                max={1}
                                                step={0.05}
                                                value={volume}
                                                onChange={handleVolumeChange}
                                                className="relative w-full h-4 appearance-none bg-transparent cursor-pointer z-10
                                                    [&::-webkit-slider-thumb]:appearance-none
                                                    [&::-webkit-slider-thumb]:w-3.5
                                                    [&::-webkit-slider-thumb]:h-3.5
                                                    [&::-webkit-slider-thumb]:rounded-full
                                                    [&::-webkit-slider-thumb]:bg-white
                                                    [&::-webkit-slider-thumb]:border-2
                                                    [&::-webkit-slider-thumb]:border-brand-500
                                                    [&::-webkit-slider-thumb]:shadow-md
                                                    [&::-webkit-slider-thumb]:cursor-pointer
                                                    [&::-webkit-slider-thumb]:transition-transform
                                                    [&::-webkit-slider-thumb]:hover:scale-110
                                                    [&::-moz-range-thumb]:w-3.5
                                                    [&::-moz-range-thumb]:h-3.5
                                                    [&::-moz-range-thumb]:rounded-full
                                                    [&::-moz-range-thumb]:bg-white
                                                    [&::-moz-range-thumb]:border-2
                                                    [&::-moz-range-thumb]:border-brand-500
                                                    [&::-moz-range-thumb]:shadow-md
                                                    [&::-moz-range-thumb]:cursor-pointer"
                                            />
                                        </div>
                                        {/* Volume percentage */}
                                        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 w-8 text-right tabular-nums">
                                            {Math.round(volume * 100)}%
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )
            }

            {/* AI Summary - Snapshot Only */}
            {
                shared.summary && (
                    <div className="card p-6 mb-6 bg-gradient-to-br from-brand-50 to-white dark:from-brand-900/10 dark:to-gray-800 border-brand-100 dark:border-brand-900/20">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-brand-100 dark:bg-brand-900/30">
                                    <Sparkles className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                                </div>
                                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">AI 智能分析</h2>
                            </div>
                        </div>

                        <div className="space-y-6">
                            {renderSection("内容摘要", shared.summary, FileText)}

                            {/* Chapters / Timeline */}
                            {shared.chapters && shared.chapters.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                        <Target className="w-4 h-4" />
                                        章节导览
                                    </h3>
                                    <div className="grid gap-2">
                                        {shared.chapters
                                            .map((c: any) => ({ ...c, timestamp: Number(c.timestamp) || 0 }))
                                            .sort((a: any, b: any) => a.timestamp - b.timestamp)
                                            .map((chapter: any, i: number) => (
                                                <button
                                                    key={i}
                                                    onClick={() => {
                                                        if (audioRef.current) {
                                                            audioRef.current.currentTime = chapter.timestamp
                                                            setCurrentTime(chapter.timestamp)
                                                            if (!isPlaying) {
                                                                audioRef.current.play()
                                                                setIsPlaying(true)
                                                            }
                                                        }
                                                    }}
                                                    className="flex items-center gap-3 p-2 text-left hover:bg-white dark:hover:bg-gray-800/50 rounded-lg transition-colors border border-transparent hover:border-brand-100 dark:hover:border-brand-900/30 group"
                                                >
                                                    <span className="text-xs font-mono text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 px-1.5 py-0.5 rounded">
                                                        {formatTime(chapter.timestamp)}
                                                    </span>
                                                    <span className="text-gray-700 dark:text-gray-300 text-sm group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors">
                                                        {chapter.title}
                                                    </span>
                                                    <Play className="w-3 h-3 text-gray-300 group-hover:text-brand-400 ml-auto opacity-0 group-hover:opacity-100 transition-all" />
                                                </button>
                                            ))}
                                    </div>
                                </div>
                            )}

                            {shared.key_points && shared.key_points.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                        <Target className="w-4 h-4" />
                                        关键要点
                                    </h3>
                                    <ul className="space-y-2">
                                        {shared.key_points.map((point: string, i: number) => (
                                            <li key={i} className="flex items-start gap-2 text-gray-700 dark:text-gray-300">
                                                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0" />
                                                <span>{point}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {shared.action_items && shared.action_items.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                        <Check className="w-4 h-4" />
                                        待办事项
                                    </h3>
                                    <ul className="space-y-2">
                                        {shared.action_items.map((item: string, i: number) => (
                                            <li key={i} className="flex items-start gap-2 text-gray-700 dark:text-gray-300">
                                                <span className="mt-1 w-4 h-4 border border-brand-400 rounded flex items-center justify-center shrink-0">
                                                    <Check className="w-3 h-3 text-transparent" />
                                                </span>
                                                <span>{item}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                )
            }

            {/* Transcript & Translation Cards */}
            <div className="space-y-4 pb-20">
                <div className="flex items-center justify-between mb-2">
                    <h2 className="text-lg font-semibold">转录详情</h2>
                    <div className="text-sm text-gray-500">
                        {shared.transcript_segments?.length || 0} 个片段
                    </div>
                </div>

                {/* Fallback if no segments */}
                {(!shared.transcript_segments || shared.transcript_segments.length === 0) && (
                    <TranscriptCard
                        transcript={shared.transcript || '暂无内容'}
                        translation={shared.translation}
                        onCopy={copyToClipboard}
                        currentTime={currentTime}
                        onSeek={handleSeek}
                        seekVersion={seekVersion}
                    />
                )}

                {/* Render Segments */}
                {shared.transcript_segments && shared.transcript_segments.map((segment: any, i: number) => {
                    const transSegment = shared.translation_segments?.[i]
                    return (
                        <TranscriptCard
                            key={i}
                            transcript={segment.text}
                            translation={transSegment?.text}
                            onCopy={copyToClipboard}
                            start={segment.start}
                            end={segment.end}
                            currentTime={currentTime}
                            onSeek={handleSeek}
                            seekVersion={seekVersion}
                        />
                    )
                })}
            </div>

            {/* Footer */}
            <footer className="text-center py-8 text-sm text-gray-400 mt-auto">
                由 Echo Text 分享
            </footer>
        </div >
    )
}

function renderSection(title: string, content: string | undefined, Icon: any) {
    if (!content) return null;
    return (
        <div>
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                <Icon className="w-4 h-4" />
                {title}
            </h3>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                {content}
            </p>
        </div>
    );
}
