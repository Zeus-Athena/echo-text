/**
 * Recording Detail Page
 * 录音详情页 - 播放、转录、翻译、搜索替换、AI总结
 */
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { recordingsApi } from '@/api/client'
import { Loader2 } from 'lucide-react'
import { useRef, useState } from 'react'

// Import sub-components
import { HeaderSection } from './recording-detail/HeaderSection'
import { AudioPlayerSection, AudioPlayerRef } from './recording-detail/AudioPlayerSection'
import { AISummarySection } from './recording-detail/AISummarySection'
import { TranscriptSection } from './recording-detail/TranscriptSection'

export default function RecordingDetailPage() {
    const { id } = useParams()
    const audioPlayerRef = useRef<AudioPlayerRef>(null)
    const [duration, setDuration] = useState(0)
    const [currentTime, setCurrentTime] = useState(0)
    const [seekVersion, setSeekVersion] = useState(0)  // 用于强制触发卡片滚动

    // add refs for seek debounce
    const ignoreUpdatesUntil = useRef(0)

    const { data: recording, isLoading } = useQuery({
        queryKey: ['recording', id],
        queryFn: () => recordingsApi.get(id!),
        select: (res) => res.data,
        enabled: !!id,
        refetchInterval: (query) => {
            const rec = query.state.data?.data
            const hasAudio = rec?.audio_size || rec?.s3_key
            // Poll while processing OR if no audio yet
            const isProcessing = ['processing', 'transcribing', 'translating', 'analyzing', 'uploaded'].includes(rec?.status)
            return (isProcessing || !hasAudio) ? 3000 : false
        },
    })

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
            </div>
        )
    }

    if (!recording) {
        return (
            <div className="text-center py-12">
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">录音不存在</h3>
            </div>
        )
    }

    const handleSeek = (timestamp: number) => {
        // 强制屏蔽 500ms 内的所有 timeUpdate 事件
        ignoreUpdatesUntil.current = Date.now() + 500

        // 立即更新 currentTime，防止旧的 active 卡片响应 seekVersion 变化而错误滚动
        setCurrentTime(timestamp)

        if (audioPlayerRef.current) {
            audioPlayerRef.current.setCurrentTime(timestamp)
            if (!audioPlayerRef.current.isPlaying) {
                audioPlayerRef.current.setIsPlaying(true)
            }
        }
        // 递增 seekVersion 以强制触发卡片滚动
        setSeekVersion(v => v + 1)
    }

    const handleTimeUpdate = (time: number) => {
        // 如果处于屏蔽期，直接忽略
        if (Date.now() < ignoreUpdatesUntil.current) {
            return
        }
        setCurrentTime(time)
    }

    return (
        <div className="h-full flex flex-col pt-4 px-4 lg:px-8 max-w-7xl mx-auto">
            <HeaderSection
                recording={recording}
                duration={duration || recording.duration_seconds}
            />

            <AudioPlayerSection
                ref={audioPlayerRef}
                recording={recording}
                id={id}
                onTimeUpdate={handleTimeUpdate}
                onSeek={() => setSeekVersion(v => v + 1)}
            />

            <AISummarySection
                recording={recording}
                id={id}
                onSeek={handleSeek}
                isPlaying={audioPlayerRef.current?.isPlaying || false}
            />

            <TranscriptSection
                recording={recording}
                currentTime={currentTime}
                onSeek={handleSeek}
                seekVersion={seekVersion}
            />
        </div>
    )
}
