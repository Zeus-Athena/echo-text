
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { recordingsApi } from '@/api/client'
import {
    Sparkles,
    RefreshCw,
    FileText,
    Target,
    Check,
    Play,
    Loader2
} from 'lucide-react'

interface AISummarySectionProps {
    recording: any
    id: string | undefined
    onSeek: (timestamp: number) => void
    isPlaying: boolean
}

export function AISummarySection({ recording, id, onSeek, isPlaying }: AISummarySectionProps) {
    const queryClient = useQueryClient()

    const summarizeMutation = useMutation({
        mutationFn: () => recordingsApi.summarize(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['recording', id] })
        },
    })

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${String(secs).padStart(2, '0')}`
    }

    if (!recording) return null

    return (
        <div className={`card p-6 mb-6 ${recording.ai_summary
            ? 'bg-gradient-to-br from-brand-50/50 to-white dark:from-brand-900/10 dark:to-gray-800 border-brand-200/50 dark:border-brand-800/50 shadow-sm shadow-brand-100/20'
            : 'bg-white dark:bg-gray-800 border-brand-100/50 dark:border-brand-900/20'}`}>

            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${recording.ai_summary ? 'bg-brand-100 dark:bg-brand-900/30' : 'bg-gray-100 dark:bg-gray-700'}`}>
                        <Sparkles className={`w-5 h-5 ${recording.ai_summary ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500'}`} />
                    </div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">AI 智能分析</h2>
                </div>

                {recording.ai_summary && (
                    <button
                        onClick={() => summarizeMutation.mutate()}
                        disabled={summarizeMutation.isPending}
                        className="p-2 text-gray-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        title="重新分析"
                    >
                        <RefreshCw className={`w-4 h-4 ${summarizeMutation.isPending ? 'animate-spin' : ''}`} />
                    </button>
                )}
            </div>

            {recording.ai_summary ? (
                <div className="space-y-6">
                    {renderSection("内容摘要", recording.ai_summary.summary, FileText)}

                    {recording.ai_summary.chapters && recording.ai_summary.chapters.length > 0 && (
                        <div>
                            <h3 className="text-sm font-medium text-brand-600/70 dark:text-brand-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                章节导览
                            </h3>
                            <div className="grid gap-2">
                                {recording.ai_summary.chapters
                                    .map((c: any) => ({ ...c, timestamp: Number(c.timestamp) || 0 }))
                                    .sort((a: any, b: any) => a.timestamp - b.timestamp)
                                    .map((chapter: any, i: number) => (
                                        <button
                                            key={i}
                                            onClick={() => onSeek(chapter.timestamp)}
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

                    {recording.ai_summary.key_points && recording.ai_summary.key_points.length > 0 && (
                        <div>
                            <h3 className="text-sm font-medium text-brand-600/70 dark:text-brand-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <Target className="w-4 h-4" />
                                关键要点
                            </h3>
                            <ul className="space-y-2">
                                {recording.ai_summary.key_points.map((point: string, i: number) => (
                                    <li key={i} className="flex items-start gap-2 text-gray-700 dark:text-gray-300">
                                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0" />
                                        <span>{point}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {recording.ai_summary.action_items && recording.ai_summary.action_items.length > 0 && (
                        <div>
                            <h3 className="text-sm font-medium text-brand-600/70 dark:text-brand-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <Check className="w-4 h-4" />
                                待办事项
                            </h3>
                            <ul className="space-y-2">
                                {recording.ai_summary.action_items.map((item: string, i: number) => (
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
                        onClick={() => summarizeMutation.mutate()}
                        disabled={summarizeMutation.isPending || !recording.transcript?.full_text}
                        className={!recording.transcript?.full_text ? "btn-secondary opacity-50 cursor-not-allowed inline-flex items-center gap-2" : "btn-primary inline-flex items-center gap-2"}
                    >
                        {summarizeMutation.isPending ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                分析中...
                            </>
                        ) : !recording.transcript?.full_text ? (
                            <span className="text-gray-400 cursor-not-allowed flex items-center gap-2">
                                <FileText className="w-4 h-4" />
                                请先完成转录
                            </span>
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

function renderSection(title: string, content: string | undefined, Icon: any) {
    if (!content) return null;
    return (
        <div>
            <h3 className="text-sm font-medium text-brand-600/70 dark:text-brand-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                <Icon className="w-4 h-4" />
                {title}
            </h3>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                {content}
            </p>
        </div>
    );
}
