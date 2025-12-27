
import TranscriptCard from '@/components/TranscriptCard'

interface TranscriptSectionProps {
    recording: any
    currentTime?: number
    onSeek?: (time: number) => void
    seekVersion?: number  // 用于强制触发卡片滚动
}

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { recordingsApi } from '@/api/client'
import { Loader2, Wand2 } from 'lucide-react'

export function TranscriptSection({ recording, currentTime, onSeek, seekVersion }: TranscriptSectionProps) {
    const queryClient = useQueryClient()
    const processMutation = useMutation({
        mutationFn: () => recordingsApi.process(recording.id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['recording', recording.id] })
        },
    })

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text)
    }

    if (!recording) return null


    return (
        <div className="space-y-4 pb-20">
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-semibold">转录详情</h2>
                <div className="text-sm text-gray-500">
                    {recording.transcript?.segments?.length || 0} 个片段
                </div>
            </div>

            {/* Fallback to full text if no segments */}
            {(!recording.transcript?.segments || recording.transcript.segments.length === 0) && (
                recording.source_type === 'upload' && !recording.transcript?.full_text ? (
                    <div className="card p-12 text-center border-2 border-dashed border-brand-200 dark:border-brand-800">
                        <div className="w-16 h-16 bg-brand-50 dark:bg-gray-800/50 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-brand-100 dark:border-brand-900/30">
                            <Wand2 className="w-8 h-8 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-medium mb-2">尚未转录</h3>
                        <p className="text-gray-500 mb-6 max-w-sm mx-auto">
                            该录音尚未生成转录文本。点击下方按钮开始自动转录和分析。
                        </p>
                        <button
                            onClick={() => processMutation.mutate()}
                            disabled={processMutation.isPending || recording.status === 'processing' || recording.status === 'transcribing'}
                            className="btn-primary"
                        >
                            {processMutation.isPending || recording.status === 'processing' || recording.status === 'transcribing' ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    正在处理...
                                </>
                            ) : (
                                <>
                                    <Wand2 className="w-4 h-4 mr-2" />
                                    开始转录 & 分析
                                </>
                            )}
                        </button>
                    </div>
                ) : (
                    <TranscriptCard
                        transcript={recording.transcript?.full_text || '暂无内容'}
                        translation={recording.translation?.full_text}
                        onCopy={copyToClipboard}
                        currentTime={currentTime}
                        onSeek={onSeek}
                        seekVersion={seekVersion}
                    />
                )
            )}

            {/* Render Segments */}
            {recording.transcript?.segments?.map((segment: any, i: number) => {
                const transSegment = recording.translation?.segments?.[i]
                return (
                    <TranscriptCard
                        key={i}
                        transcript={segment.text}
                        translation={transSegment?.text}
                        onCopy={copyToClipboard}
                        start={segment.start}
                        end={segment.end}
                        currentTime={currentTime}
                        onSeek={onSeek}
                        seekVersion={seekVersion}
                    />
                )
            })}
        </div>
    )
}
