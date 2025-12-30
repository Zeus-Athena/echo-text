
import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { recordingsApi, userApi } from '@/api/client'
import { useRealtimeSTT } from '@/hooks/useRealtimeSTT'
import { useNoiseDetection } from '@/hooks/useNoiseDetection'
import {
    Mic,
    X,
    Loader2,
    Play,
    Pause,
    RefreshCw,
    Square,
    Languages,
    FileText
} from 'lucide-react'
import clsx from 'clsx'
import TranscriptCard from '@/components/TranscriptCard'
import { PartyAudioVisualizer } from '@/components/PartyAudioVisualizer'
import { FileManagerPanel } from '@/components/FileManagerPanel'

type TabType = 'realtime' | 'records'

export default function RecordingsPage() {
    const [searchParams, setSearchParams] = useSearchParams()

    // Tab state - initialize from URL, default to 'realtime' if no folder context
    const initialTab = searchParams.get('tab') === 'records' || searchParams.get('folder_id') ? 'records' : 'realtime'
    const [activeTab, setActiveTab] = useState<TabType>(initialTab)

    // Helper to update search params preserving folder_id
    const updateTabParam = (tab: TabType) => {
        const newParams = new URLSearchParams(searchParams)
        newParams.set('tab', tab)
        setSearchParams(newParams)
    }

    return (
        <div className="flex h-[calc(100vh-64px)]">
            {/* Left Tab Bar */}
            <div className="w-20 flex-shrink-0 bg-brand-50/10 dark:bg-gray-900 border-r border-brand-200/60 dark:border-brand-800/60 flex flex-col">
                <button
                    onClick={() => {
                        setActiveTab('realtime')
                        updateTabParam('realtime')
                    }}
                    className={clsx(
                        'flex flex-col items-center justify-center py-5 px-2 border-b border-brand-100 dark:border-brand-800 transition-colors',
                        activeTab === 'realtime'
                            ? 'bg-white dark:bg-gray-800 text-brand-600 border-l-2 border-l-brand-500'
                            : 'hover:bg-brand-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                    )}
                >
                    <Languages className="w-6 h-6 mb-1" />
                    <span className="text-xs font-medium">实时翻译</span>
                </button>
                <button
                    onClick={() => {
                        setActiveTab('records')
                        updateTabParam('records')
                    }}
                    className={clsx(
                        'flex flex-col items-center justify-center py-5 px-2 border-b border-brand-100 dark:border-brand-800 transition-colors',
                        activeTab === 'records'
                            ? 'bg-white dark:bg-gray-800 text-brand-600 border-l-2 border-l-brand-500'
                            : 'hover:bg-brand-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                    )}
                >
                    <FileText className="w-6 h-6 mb-1" />
                    <span className="text-xs font-medium">记录</span>
                </button>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden">
                {activeTab === 'realtime' ? (
                    <RealtimeRecordingPanel />
                ) : (
                    <FileManagerPanel sourceType="realtime" />
                )}
            </div>
        </div>
    )
}

// Real-time Recording Panel (embedded in page, not modal)
function RealtimeRecordingPanel() {
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const { data: config } = useQuery({
        queryKey: ['user-config'],
        queryFn: () => userApi.getConfig(),
        select: (res) => res.data,
    })

    // Track if auto-detection has happened
    const [autoDetectedThreshold, setAutoDetectedThreshold] = useState<number | null>(null)

    // Determine effective threshold based on prefer source
    const silencePreferSource = config?.recording?.silence_prefer_source ?? 'current'
    const configThreshold = config?.recording?.silence_threshold ?? 30

    // Effective threshold to use
    // 'current' (or legacy 'manual'): use config threshold
    // 'auto': use auto-detected if available, otherwise config
    const effectiveThreshold = (() => {
        if (silencePreferSource === 'current' || silencePreferSource === 'manual') {
            return configThreshold
        }
        // Prefer auto - use auto-detected if available, otherwise config
        return autoDetectedThreshold ?? configThreshold
    })()

    // Noise detection hook for auto-detection on recording start
    const { detectNoise } = useNoiseDetection()

    // Pause state - must be declared before the hook that uses it
    const [isPaused, setIsPaused] = useState(false)

    const stt = useRealtimeSTT({
        silenceThreshold: effectiveThreshold,
        bufferDuration: config?.recording?.audio_buffer_duration ?? 6,
        isPaused: isPaused,
        segmentSoftThreshold: config?.recording?.segment_soft_threshold ?? 50,
        segmentHardThreshold: config?.recording?.segment_hard_threshold ?? 100,
    })

    const [title, setTitle] = useState('')
    const [sourceLang, setSourceLang] = useState('en')
    const [targetLang, setTargetLang] = useState('zh')
    const [step, setStep] = useState<'ready' | 'recording' | 'saving'>('ready')
    const [recordingId, setRecordingId] = useState<string | null>(null)
    const [isStarting, setIsStarting] = useState(false)
    const [startError, setStartError] = useState<string | null>(null)
    const [showCancelConfirm, setShowCancelConfirm] = useState(false)

    // Auto-scroll ref
    const scrollContainerRef = useRef<HTMLDivElement>(null)

    // Auto-scroll when segments or transcript changes
    useEffect(() => {
        if (step === 'recording' && scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight
        }
    }, [step, stt.segments, stt.transcript, stt.translation])

    // Create recording at start (to get ID for audio saving)
    const createRecordingMutation = useMutation({
        mutationFn: async () => {
            const res = await recordingsApi.create({
                title: title || `录音 ${new Date().toLocaleString()}`,
                source_lang: sourceLang,
                target_lang: targetLang,
            })
            return res.data
        },
    })

    // Save transcript/translation after recording
    const saveTranscriptMutation = useMutation({
        mutationFn: async ({
            id,
            transcript,
            translation,
            transcriptSegments,
            translationSegments
        }: {
            id: string;
            transcript: string;
            translation: string;
            transcriptSegments?: any[];
            translationSegments?: any[];
        }) => {
            if (transcript) {
                await recordingsApi.updateTranscript(id, {
                    full_text: transcript,
                    segments: transcriptSegments
                })
            }
            if (translation) {
                await recordingsApi.updateTranslation(id, {
                    full_text: translation,
                    segments: translationSegments
                })
            }
            return id
        },
        onSuccess: (id) => {
            queryClient.invalidateQueries({ queryKey: ['recordings'] })
            queryClient.invalidateQueries({ queryKey: ['folders'] }) // Refresh folder counts
            navigate(`/recordings/${id}`)
        },
    })

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${String(secs).padStart(2, '0')}`
    }

    const handleStart = async () => {
        setIsStarting(true)
        setStartError(null)
        try {
            // If prefer auto + not yet detected, trigger async detection
            if (silencePreferSource === 'auto' && autoDetectedThreshold === null) {
                // Start async noise detection (non-blocking)
                detectNoise().then((detected) => {
                    setAutoDetectedThreshold(detected)
                    console.log(`[Recording] Auto-detected threshold: ${detected}`)
                }).catch((err) => {
                    console.warn('[Recording] Auto-detection failed, using config value:', err)
                })
            }

            const recording = await createRecordingMutation.mutateAsync()
            setRecordingId(recording.id)
            await stt.startRecording(sourceLang, targetLang, recording.id)
            setStep('recording')
        } catch (e) {
            console.error('Failed to start recording:', e)
            const errorMsg = e instanceof Error ? e.message : '录音启动失败，请检查麦克风权限或网络连接'
            setStartError(errorMsg)
        } finally {
            setIsStarting(false)
        }
    }

    const handleStop = async () => {
        const result = await stt.stopRecording()
        if (recordingId) {
            setStep('saving')
            // 发送 segments 到后端保存，时间戳已经是后端提供的精确值
            saveTranscriptMutation.mutate({
                id: recordingId,
                transcript: result.transcript,
                translation: result.translation,
                transcriptSegments: result.segments.map((s) => ({
                    start: s.start,
                    end: s.end,
                    text: s.text
                })),
                translationSegments: result.segments.map((s) => ({
                    start: s.start,
                    end: s.end,
                    text: s.translation
                }))
            })
        }
    }

    const handleReset = () => {
        stt.resetState()
        setStep('ready')
        setRecordingId(null)
        setTitle('')
        setStartError(null)
        setIsPaused(false)
    }

    const handleCancel = () => {
        setShowCancelConfirm(true)
    }

    const confirmCancel = () => {
        stt.resetState()
        setStep('ready')
        setRecordingId(null)
        setTitle('')
        setStartError(null)
        setIsPaused(false)
        setShowCancelConfirm(false)
    }

    const handlePauseResume = () => {
        setIsPaused(prev => !prev)
        // Note: Pause is frontend-only, audio chunks stop being sent while paused
        // The MediaRecorder continues but we don't forward to WebSocket
    }

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text)
    }

    return (
        <div className="h-full flex flex-col pt-6 px-0 pb-6">
            {/* Header - added horizontal padding back */}
            <div className="flex items-center justify-between mb-6 px-6">
                <div>
                    <h1 className="text-2xl font-bold">实时翻译</h1>
                    <p className="text-gray-500 text-sm mt-1">实时语音转录和翻译</p>
                </div>

                {/* Center: Party Visualizer (only when recording) */}
                {step === 'recording' && (
                    <div className="flex-1 flex justify-center">
                        <PartyAudioVisualizer volume={stt.currentVolume} />
                    </div>
                )}

                {step === 'recording' && (
                    <div className="flex items-center gap-3">
                        {/* Connection Status Indicator (方案 A) */}
                        {stt.connectionStatus === 'reconnecting' ? (
                            <>
                                <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />
                                <span className="text-yellow-500 font-medium">重连中...</span>
                            </>
                        ) : stt.connectionStatus === 'disconnected' ? (
                            <>
                                <X className="w-4 h-4 text-gray-400" />
                                <span className="text-gray-400 font-medium">连接断开</span>
                            </>
                        ) : isPaused ? (
                            <>
                                <span className="w-3 h-3 bg-yellow-500 rounded-full" />
                                <span className="text-yellow-500 font-medium">已暂停</span>
                            </>
                        ) : (
                            <>
                                <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                                <span className="text-red-500 font-medium">REC</span>
                            </>
                        )}
                        <span className="text-2xl font-mono">{formatTime(stt.duration)}</span>
                        {/* Volume Meter */}
                        <div className="flex items-center gap-1.5 ml-2">
                            <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500 transition-all duration-75"
                                    style={{ width: `${stt.currentVolume}%` }}
                                />
                            </div>
                            <span className="text-xs text-gray-500 w-8">{stt.currentVolume}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Content - Global scrollbar at the right edge */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0" ref={scrollContainerRef}>
                {step === 'ready' ? (
                    <div className="h-full flex flex-col items-center justify-center px-6">
                        <div className="w-32 h-32 rounded-full bg-gradient-to-br from-brand-100 to-brand-200 dark:from-brand-900/30 dark:to-brand-800/30 flex items-center justify-center mb-6">
                            <Mic className="w-16 h-16 text-brand-500" />
                        </div>
                        <p className="text-gray-500 mb-8">设置参数后点击开始录音</p>

                        <div className="w-full max-w-md space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1.5">标题</label>
                                <input
                                    type="text"
                                    placeholder="录音标题（可选）"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    className="input"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1.5">源语言</label>
                                    <select
                                        value={sourceLang}
                                        onChange={(e) => setSourceLang(e.target.value)}
                                        className="input"
                                    >
                                        <option value="en">English</option>
                                        <option value="zh">中文</option>
                                        <option value="ja">日本語</option>
                                        <option value="ko">한국어</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1.5">目标语言</label>
                                    <select
                                        value={targetLang}
                                        onChange={(e) => setTargetLang(e.target.value)}
                                        className="input"
                                    >
                                        <option value="zh">中文</option>
                                        <option value="en">English</option>
                                        <option value="ja">日本語</option>
                                        <option value="ko">한국어</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : step === 'recording' ? (
                    <div
                        className="w-full flex flex-col gap-6 p-6"
                    >
                        {/* Historical Segments */}
                        {stt.segments.map((seg, i) => {
                            const isLastAndActive = i === stt.segments.length - 1 && seg.isFinal === false
                            return (
                                <TranscriptCard
                                    key={seg.id || i}
                                    transcript={seg.text}
                                    translation={seg.translation}
                                    isFinal={seg.isFinal ?? true}
                                    interimTranscript={isLastAndActive ? stt.interimTranscript : undefined}
                                    interimTranslation={isLastAndActive ? stt.interimTranslation : undefined}
                                    onCopy={copyToClipboard}
                                />
                            )
                        })}

                        {/* Current Segment (Legacy Mode or Fallback) */}
                        {/* Only show if we strictly have no active segment in list to avoid duplication */}
                        {(!stt.segments.length || stt.segments[stt.segments.length - 1].isFinal !== false) &&
                            (stt.transcript || stt.translation || stt.interimTranscript) && (
                                <TranscriptCard
                                    transcript={stt.transcript}
                                    translation={stt.translation}
                                    interimTranscript={stt.interimTranscript}
                                    interimTranslation={stt.interimTranslation}
                                    isFinal={false}
                                    onCopy={copyToClipboard}
                                    className="border-brand-200 dark:border-brand-800 ring-1 ring-brand-100 dark:ring-brand-900"
                                />
                            )}
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center">
                        <Loader2 className="w-16 h-16 text-brand-500 animate-spin mb-4" />
                        <p className="text-gray-500">正在保存录音...</p>
                    </div>
                )}
            </div>

            {/* Footer Controls */}
            <div className="flex justify-center gap-4 pt-6 border-t border-brand-200/60 dark:border-brand-800/60 mt-6">
                {step === 'ready' && (
                    <button
                        onClick={handleStart}
                        disabled={isStarting}
                        className="btn-primary px-8 py-3 flex items-center gap-2 disabled:opacity-50"
                    >
                        {isStarting ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Mic className="w-5 h-5" />
                        )}
                        {isStarting ? '连接中...' : '开始录音'}
                    </button>
                )}

                {step === 'recording' && (
                    <>
                        {/* Cancel Button */}
                        <button
                            onClick={handleCancel}
                            className="btn-secondary px-6 py-3 flex items-center gap-2"
                        >
                            <X className="w-5 h-5" />
                            取消
                        </button>

                        {/* Pause/Resume Button */}
                        <button
                            onClick={handlePauseResume}
                            className={`px-6 py-3 rounded-lg flex items-center gap-2 ${isPaused
                                ? 'bg-green-500 hover:bg-green-600 text-white'
                                : 'bg-yellow-500 hover:bg-yellow-600 text-white'
                                }`}
                        >
                            {isPaused ? (
                                <>
                                    <Play className="w-5 h-5" />
                                    继续
                                </>
                            ) : (
                                <>
                                    <Pause className="w-5 h-5" />
                                    暂停
                                </>
                            )}
                        </button>

                        {/* Stop Button */}
                        <button
                            onClick={handleStop}
                            className="bg-red-500 hover:bg-red-600 text-white px-8 py-3 rounded-lg flex items-center gap-2"
                        >
                            <Square className="w-5 h-5" />
                            停止录音
                        </button>
                    </>
                )}
            </div>

            {/* Error */}
            {(stt.error || startError) && (
                <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-sm">
                    {startError || stt.error}
                </div>
            )}

            {/* Cancel Confirmation Modal */}
            {showCancelConfirm && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-sm w-full mx-4 p-6 border border-brand-200 dark:border-brand-800">
                        <h3 className="text-lg font-semibold mb-2">取消录音</h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            确定要取消录音吗？已录制的内容将不会保存。
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowCancelConfirm(false)}
                                className="btn-secondary px-4 py-2"
                            >
                                继续录音
                            </button>
                            <button
                                onClick={confirmCancel}
                                className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg"
                            >
                                确认取消
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
