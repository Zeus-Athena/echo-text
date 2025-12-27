import { Copy, Check, Clock } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

interface TranscriptCardProps {
    transcript: string
    translation?: string
    isFinal?: boolean
    onCopy: (text: string) => void
    className?: string
    // Interim 实时文本 (灰色斜体)
    interimTranscript?: string
    interimTranslation?: string
    // 时间戳和播放控制
    start?: number
    end?: number
    currentTime?: number
    onSeek?: (time: number) => void
    // 每次 seek 操作时递增，用于强制触发滚动
    seekVersion?: number
}

// 格式化时间显示
const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${String(secs).padStart(2, '0')}`
}

export default function TranscriptCard({
    transcript,
    translation,
    isFinal = true,
    onCopy,
    className = '',
    interimTranscript,
    interimTranslation,
    start,
    end,
    currentTime,
    onSeek,
    seekVersion
}: TranscriptCardProps) {
    const [copiedSrc, setCopiedSrc] = useState(false)
    const [copiedTrans, setCopiedTrans] = useState(false)
    const cardRef = useRef<HTMLDivElement>(null)

    const handleCopy = (text: string, type: 'src' | 'trans') => {
        onCopy(text)
        if (type === 'src') {
            setCopiedSrc(true)
            setTimeout(() => setCopiedSrc(false), 2000)
        } else {
            setCopiedTrans(true)
            setTimeout(() => setCopiedTrans(false), 2000)
        }
    }

    // 记录是否曾经播放过（用户点击播放或 seek 过）
    const hasEverPlayedRef = useRef(false)

    // 当 currentTime > 0 时，标记为已播放过
    useEffect(() => {
        if (currentTime !== undefined && currentTime > 0) {
            hasEverPlayedRef.current = true
        }
    }, [currentTime])

    // 判断当前卡片是否正在播放（高亮）
    // 对于第一张卡片 (start < 0.1)，如果曾播放过，允许 currentTime=0 时也高亮
    const isInRange = start !== undefined && end !== undefined &&
        currentTime !== undefined && currentTime >= start && currentTime < end
    const isFirstCard = start !== undefined && start < 0.1
    const isActive = isInRange && (hasEverPlayedRef.current || currentTime! > 0 || isFirstCard)

    // 是否可点击跳转
    const isClickable = onSeek && start !== undefined

    const handleCardClick = () => {
        if (isClickable) {
            onSeek(start)
        }
    }

    // 当卡片变为高亮状态时，或用户主动 seek 到当前卡片时，自动滚动到可视区域
    const prevActiveRef = useRef(false)
    const prevSeekVersionRef = useRef(seekVersion)

    useEffect(() => {
        const isNewlyActive = isActive && !prevActiveRef.current
        const isSeekToThis = isActive && seekVersion !== prevSeekVersionRef.current

        // 当状态从 false 变为 true，或者 seekVersion 变化且卡片活跃时触发滚动
        if ((isNewlyActive || isSeekToThis) && cardRef.current) {
            // 使用 setTimeout 确保在 React 完成所有 DOM 更新和布局重排后再滚动
            // 这可以防止因其他卡片样式变化导致的高度塌陷从而引起错误的滚动
            setTimeout(() => {
                cardRef.current?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                })
            }, 10)
        }

        prevActiveRef.current = isActive
        prevSeekVersionRef.current = seekVersion
    }, [isActive, seekVersion])

    return (
        <div
            ref={cardRef}
            onClick={handleCardClick}
            className={`
                bg-brand-50 dark:bg-gray-900/50 rounded-xl shadow-sm border overflow-hidden
                transition-all duration-300 ease-out
                ${isActive
                    ? 'border-brand-400 dark:border-brand-500 ring-2 ring-brand-400/30 dark:ring-brand-500/30 shadow-lg scale-[1.01]'
                    : 'border-brand-100 dark:border-brand-900/50'
                }
                ${isClickable
                    ? 'cursor-pointer hover:shadow-md hover:border-brand-200 dark:hover:border-brand-800'
                    : ''
                }
                ${className}
            `}
        >
            {/* 时间戳标签 - 仅当有时间信息时显示 */}
            {start !== undefined && (
                <div className={`
                    px-4 py-1.5 flex items-center gap-1.5 text-xs font-medium
                    border-b transition-colors duration-300
                    ${isActive
                        ? 'bg-brand-100 dark:bg-brand-900/50 text-brand-600 dark:text-brand-400 border-brand-200 dark:border-brand-800'
                        : 'bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-brand-100/50 dark:border-brand-900/50'
                    }
                `}>
                    <Clock className="w-3 h-3" />
                    <span>{formatTime(start)}</span>
                    {end !== undefined && (
                        <>
                            <span className="text-gray-300 dark:text-gray-600">—</span>
                            <span>{formatTime(end)}</span>
                        </>
                    )}
                    {isActive && (
                        <span className="ml-2 flex items-center gap-1 text-brand-500">
                            <span className="w-1.5 h-1.5 bg-brand-500 rounded-full animate-pulse" />
                            播放中
                        </span>
                    )}
                </div>
            )}

            {/* Transcript Section */}
            <div className="p-4 border-b border-brand-100/50 dark:border-brand-900/50">
                <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                        <p className={`text-gray-800 dark:text-gray-200 text-base leading-relaxed ${!isFinal ? 'opacity-70' : ''}`}>
                            {transcript}
                            {/* Interim Transcript (灰色斜体，紧跟在确认文字后) */}
                            {interimTranscript && (
                                <span className="text-gray-400 dark:text-gray-500 italic animate-pulse">
                                    {transcript ? ' ' : ''}{interimTranscript}
                                </span>
                            )}
                        </p>
                    </div>
                    <button
                        onClick={(e) => {
                            e.stopPropagation()
                            handleCopy(transcript, 'src')
                        }}
                        className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg transition-colors flex-shrink-0"
                        title="复制原文"
                    >
                        {copiedSrc ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {/* Translation Section */}
            {(translation || interimTranslation || !isFinal) && (
                <div className="p-4 bg-brand-100 dark:bg-gray-800">
                    <div className="flex justify-between items-start gap-4">
                        <div className="flex-1">
                            <p className="text-gray-600 dark:text-gray-400 text-base leading-relaxed">
                                {translation || (
                                    !interimTranslation && <span className="animate-pulse">翻译中...</span>
                                )}
                                {/* Interim Translation (灰色斜体，紧跟在确认译文后) */}
                                {interimTranslation && (
                                    <span className="text-gray-400 dark:text-gray-500 italic animate-pulse">
                                        {translation ? ' ' : ''}{interimTranslation}
                                    </span>
                                )}
                            </p>
                        </div>
                        {translation && (
                            <button
                                onClick={(e) => {
                                    e.stopPropagation()
                                    handleCopy(translation, 'trans')
                                }}
                                className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors flex-shrink-0"
                                title="复制译文"
                            >
                                {copiedTrans ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
