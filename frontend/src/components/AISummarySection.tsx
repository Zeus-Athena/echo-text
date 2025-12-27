/**
 * AISummarySection Component
 * AI 智能分析区域组件
 */
import { memo } from 'react'
import {
    FileText,
    Target,
    Sparkles,
    Check,
    Loader2,
    RefreshCw,
    Play,
} from 'lucide-react'

interface Chapter {
    timestamp: number
    title: string
}

interface AISummaryData {
    summary?: string
    chapters?: Chapter[]
    key_points?: string[]
    action_items?: string[]
}

interface AISummarySectionProps {
    aiSummary: AISummaryData | null
    isPending: boolean
    onSummarize: () => void
    onSeekToChapter: (timestamp: number) => void
    formatTime: (seconds: number) => string
}

function AISummarySectionComponent({
    aiSummary,
    isPending,
    onSummarize,
    onSeekToChapter,
    formatTime
}: AISummarySectionProps) {
    return (
        <div className={`card p-6 mb-6 ${aiSummary
            ? 'bg-gradient-to-br from-brand-50 to-white dark:from-brand-900/10 dark:to-gray-800 border-brand-100 dark:border-brand-900/20'
            : 'bg-white dark:bg-gray-800 border-gray-100 dark:border-gray-700'}`}>

            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${aiSummary ? 'bg-brand-100 dark:bg-brand-900/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
                        <Sparkles className={`w-5 h-5 ${aiSummary ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500'}`} />
                    </div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">AI 智能分析</h2>
                </div>

                {aiSummary && (
                    <button
                        onClick={onSummarize}
                        disabled={isPending}
                        className="p-2 text-gray-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        title="重新分析"
                    >
                        <RefreshCw className={`w-4 h-4 ${isPending ? 'animate-spin' : ''}`} />
                    </button>
                )}
            </div>

            {aiSummary ? (
                <div className="space-y-6">
                    {/* Summary Section */}
                    {aiSummary.summary && (
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <FileText className="w-4 h-4" />
                                内容摘要
                            </h3>
                            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                                {aiSummary.summary}
                            </p>
                        </div>
                    )}

                    {/* Chapters / Timeline */}
                    {aiSummary.chapters && aiSummary.chapters.length > 0 && (
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                章节导览
                            </h3>
                            <div className="grid gap-2">
                                {aiSummary.chapters
                                    .map((c) => ({ ...c, timestamp: Number(c.timestamp) || 0 }))
                                    .sort((a, b) => a.timestamp - b.timestamp)
                                    .map((chapter, i) => (
                                        <button
                                            key={i}
                                            onClick={() => onSeekToChapter(chapter.timestamp)}
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

                    {/* Key Points */}
                    {aiSummary.key_points && aiSummary.key_points.length > 0 && (
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                关键要点
                            </h3>
                            <ul className="space-y-2">
                                {aiSummary.key_points.map((point, i) => (
                                    <li key={i} className="flex items-start gap-2 text-gray-700 dark:text-gray-300">
                                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0" />
                                        <span>{point}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Action Items */}
                    {aiSummary.action_items && aiSummary.action_items.length > 0 && (
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <Check className="w-4 h-4" />
                                待办事项
                            </h3>
                            <ul className="space-y-2">
                                {aiSummary.action_items.map((item, i) => (
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
            ) : (
                <div className="text-center py-8">
                    <p className="text-gray-500 mb-6">暂无 AI 分析内容，点击下方按钮开始分析。</p>
                    <button
                        onClick={onSummarize}
                        disabled={isPending}
                        className="btn-primary inline-flex items-center gap-2"
                    >
                        {isPending ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                分析中...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-4 h-4" />
                                开始 AI 分析
                            </>
                        )}
                    </button>
                </div>
            )}
        </div>
    )
}

export const AISummarySection = memo(AISummarySectionComponent)
