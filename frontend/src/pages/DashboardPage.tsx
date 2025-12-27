/**
 * Dashboard Page
 * 首页 - 显示统计和快捷操作
 */
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth'
import { recordingsApi } from '@/api/client'
import {
    Mic,
    Languages,
    AudioWaveform,
    BookOpen,
    Clock,
    FileText,
    ArrowRight,
} from 'lucide-react'

export default function DashboardPage() {
    const { user } = useAuthStore()
    const navigate = useNavigate()

    // Fetch recent recordings
    const { data: recordingsData } = useQuery({
        queryKey: ['recordings', 'recent'],
        queryFn: () => recordingsApi.list({ limit: 5 }),
        select: (res) => res.data,
    })

    const recordings = recordingsData?.items || []

    const quickActions = [
        {
            name: '开始录音',
            description: '实时转录和翻译',
            icon: Mic,
            color: 'bg-red-500',
            href: '/recordings?new=true',
        },
        {
            name: '文本翻译',
            description: '输入或粘贴文本',
            icon: Languages,
            color: 'bg-blue-500',
            href: '/text-translate',
        },
        {
            name: '语音翻译',
            description: '上传音频文件',
            icon: AudioWaveform,
            color: 'bg-purple-500',
            href: '/voice-translate',
        },
        {
            name: '查词典',
            description: '查询单词释义',
            icon: BookOpen,
            color: 'bg-green-500',
            href: '/dictionary',
        },
    ]

    return (
        <div className="px-4 lg:px-8 py-6 max-w-7xl mx-auto">
            {/* Welcome */}
            <div className="mb-8">
                <h1 className="text-2xl font-bold">
                    欢迎回来，{user?.username}！
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                    开始使用 EchoText 进行实时转录和翻译
                </p>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                {quickActions.map((action) => (
                    <button
                        key={action.name}
                        onClick={() => navigate(action.href)}
                        className="card p-6 text-left hover:shadow-md transition-shadow group"
                    >
                        <div
                            className={`w-12 h-12 rounded-xl ${action.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
                        >
                            <action.icon className="w-6 h-6 text-white" />
                        </div>
                        <h3 className="font-semibold">{action.name}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {action.description}
                        </p>
                    </button>
                ))}
            </div>

            {/* Recent Recordings */}
            <div className="card">
                <div className="flex items-center justify-between p-4 border-b border-brand-100 dark:border-brand-800/60">
                    <h2 className="font-semibold text-brand-700 dark:text-brand-300">最近录音</h2>
                    <button
                        onClick={() => navigate('/recordings')}
                        className="text-sm text-brand-600 hover:text-brand-700 flex items-center gap-1"
                    >
                        查看全部 <ArrowRight className="w-4 h-4" />
                    </button>
                </div>

                {recordings && recordings.length > 0 ? (
                    <div className="divide-y divide-brand-50/50 dark:divide-brand-900/20">
                        {recordings.map((recording: any) => (
                            <button
                                key={recording.id}
                                onClick={() => navigate(`/recordings/${recording.id}`)}
                                className="w-full flex items-center gap-4 p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors text-left"
                            >
                                <div className="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                                    <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-medium truncate">{recording.title}</h3>
                                    <p className="text-sm text-gray-500 flex items-center gap-2 mt-0.5">
                                        <Clock className="w-3 h-3" />
                                        {Math.floor(recording.duration_seconds / 60)}:{String(recording.duration_seconds % 60).padStart(2, '0')}
                                        <span>•</span>
                                        {recording.source_lang.toUpperCase()} → {recording.target_lang.toUpperCase()}
                                    </p>
                                </div>
                                <ArrowRight className="w-4 h-4 text-gray-400" />
                            </button>
                        ))}
                    </div>
                ) : (
                    <div className="p-8 text-center text-gray-500">
                        <Mic className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p>还没有录音记录</p>
                        <button
                            onClick={() => navigate('/recordings?new=true')}
                            className="btn-primary mt-4"
                        >
                            开始第一次录音
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
