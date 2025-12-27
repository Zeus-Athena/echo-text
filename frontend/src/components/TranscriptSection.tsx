/**
 * TranscriptSection Component
 * 转录详情区域组件
 */
import { memo } from 'react'
import TranscriptCard from './TranscriptCard'

interface Segment {
    text: string
    start?: number
    end?: number
}

interface TranscriptData {
    full_text?: string
    segments?: Segment[]
}

interface TranslationData {
    full_text?: string
    segments?: Segment[]
}

interface TranscriptSectionProps {
    transcript: TranscriptData | null
    translation: TranslationData | null
    onCopy: (text: string) => void
}

function TranscriptSectionComponent({
    transcript,
    translation,
    onCopy
}: TranscriptSectionProps) {
    const segmentCount = transcript?.segments?.length || 0
    const hasSegments = segmentCount > 0

    return (
        <div className="space-y-4 pb-20">
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-semibold">转录详情</h2>
                <div className="text-sm text-gray-500">
                    {segmentCount} 个片段
                </div>
            </div>

            {/* Fallback to full text if no segments */}
            {!hasSegments && (
                <TranscriptCard
                    transcript={transcript?.full_text || '暂无内容'}
                    translation={translation?.full_text}
                    onCopy={onCopy}
                />
            )}

            {/* Render Segments */}
            {transcript?.segments?.map((segment, i) => {
                const transSegment = translation?.segments?.[i]
                return (
                    <TranscriptCard
                        key={i}
                        transcript={segment.text}
                        translation={transSegment?.text}
                        onCopy={onCopy}
                    />
                )
            })}
        </div>
    )
}

export const TranscriptSection = memo(TranscriptSectionComponent)
