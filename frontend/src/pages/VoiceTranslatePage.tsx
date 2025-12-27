
/**
 * Voice Translate Page
 * 语音翻译页 - Tab 结构：上传音频 / 记录
 */
import { useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { recordingsApi } from '@/api/client'
import { Upload, Mic, FileAudio, X, Loader2, FileText } from 'lucide-react'
import clsx from 'clsx'
import { FileManagerPanel } from '@/components/FileManagerPanel'

type TabType = 'upload' | 'records'

export default function VoiceTranslatePage() {
    const [searchParams] = useSearchParams()
    const initialTab = (searchParams.get('tab') === 'records') ? 'records' : 'upload'
    const [activeTab, setActiveTab] = useState<TabType>(initialTab)

    return (
        <div className="flex h-[calc(100vh-64px)]">
            {/* Left Tab Bar */}
            <div className="w-20 flex-shrink-0 bg-brand-50/10 dark:bg-gray-900 border-r border-brand-200/60 dark:border-brand-800/60 flex flex-col">
                <button
                    onClick={() => setActiveTab('upload')}
                    className={clsx(
                        'flex flex-col items-center justify-center py-5 px-2 border-b border-brand-100 dark:border-brand-800 transition-colors',
                        activeTab === 'upload'
                            ? 'bg-white dark:bg-gray-800 text-brand-600 border-l-2 border-l-brand-500'
                            : 'hover:bg-brand-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                    )}
                >
                    <Upload className="w-6 h-6 mb-1" />
                    <span className="text-xs font-medium">上传音频</span>
                </button>
                <button
                    onClick={() => setActiveTab('records')}
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
                {activeTab === 'upload' ? (
                    <UploadPanel onUploadSuccess={() => setActiveTab('records')} />
                ) : (
                    <FileManagerPanel sourceType="upload" pollingInterval={5000} />
                )}
            </div>
        </div>
    )
}

// Upload Panel
function UploadPanel({ onUploadSuccess }: { onUploadSuccess: () => void }) {
    const navigate = useNavigate()
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [file, setFile] = useState<File | null>(null)
    const [dragOver, setDragOver] = useState(false)
    const [sourceLang, setSourceLang] = useState('en')
    const [targetLang, setTargetLang] = useState('zh')
    const [title, setTitle] = useState('')
    const [autoProcess, setAutoProcess] = useState(false)

    const queryClient = useQueryClient()

    const uploadMutation = useMutation({
        mutationFn: async () => {
            if (!file) throw new Error('请选择文件')

            const res = await recordingsApi.upload(file, {
                title: title || file.name.replace(/\.[^/.]+$/, ''),
                source_lang: sourceLang,
                target_lang: targetLang,
                auto_process: autoProcess,
            })
            return res.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['recordings'] }) // Refresh shared recordings query
            queryClient.invalidateQueries({ queryKey: ['folders'] }) // Refresh folder counts
            setFile(null)
            setTitle('')
            onUploadSuccess()
        }
    })

    const handleFileSelect = (selectedFile: File) => {
        if (selectedFile && selectedFile.type.startsWith('audio/')) {
            setFile(selectedFile)
        }
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setDragOver(false)
        const droppedFile = e.dataTransfer.files[0]
        if (droppedFile) {
            handleFileSelect(droppedFile)
        }
    }

    return (
        <div className="h-full overflow-y-auto p-8 flex flex-col items-center">
            <div className="w-full max-w-4xl">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold mb-3">语音翻译</h1>
                    <p className="text-gray-500">上传音频文件，自动转录并翻译</p>
                </div>

                {/* Language Selection - centered */}
                <div className="card p-6 mb-8">
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
                                <option value="es">Español</option>
                                <option value="fr">Français</option>
                                <option value="de">Deutsch</option>
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
                                <option value="es">Español</option>
                                <option value="fr">Français</option>
                                <option value="de">Deutsch</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Upload Area - Large and Centered */}
                <div
                    onDragOver={(e) => {
                        e.preventDefault()
                        setDragOver(true)
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    className={`card p-16 border-2 border-dashed transition-all duration-300 min-h-[320px] flex items-center justify-center ${dragOver
                        ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 scale-[1.02]'
                        : 'border-brand-200 dark:border-brand-800 hover:border-brand-300 dark:hover:border-brand-700'
                        }`}
                >
                    {file ? (
                        <div className="text-center">
                            <div className="w-16 h-16 rounded-2xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center mx-auto mb-4">
                                <FileAudio className="w-8 h-8 text-brand-600 dark:text-brand-400" />
                            </div>
                            <p className="font-medium">{file.name}</p>
                            <p className="text-sm text-gray-500 mt-1">
                                {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>

                            {/* Title Input */}
                            <div className="mt-4 max-w-xs mx-auto">
                                <input
                                    type="text"
                                    placeholder="标题（可选）"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    className="input text-center"
                                />
                            </div>

                            {/* Auto Process Checkbox */}
                            <label className="flex items-center justify-center gap-2 mt-4 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={autoProcess}
                                    onChange={(e) => setAutoProcess(e.target.checked)}
                                    className="w-4 h-4 text-brand-600 rounded"
                                />
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                    上传后自动开始转录翻译
                                </span>
                            </label>

                            <div className="flex items-center justify-center gap-3 mt-6">
                                <button
                                    onClick={() => setFile(null)}
                                    className="btn-secondary"
                                >
                                    <X className="w-4 h-4 mr-2" />
                                    取消
                                </button>
                                <button
                                    onClick={() => uploadMutation.mutate()}
                                    disabled={uploadMutation.isPending}
                                    className="btn-primary"
                                >
                                    {uploadMutation.isPending ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <>
                                            <Upload className="w-4 h-4 mr-2" />
                                            上传
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center">
                            <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-4">
                                <Upload className="w-8 h-8 text-gray-400" />
                            </div>
                            <p className="font-medium">拖拽音频文件到这里</p>
                            <p className="text-sm text-gray-500 mt-1">
                                支持 MP3, WAV, M4A, FLAC, WebM (最大 100MB)
                            </p>
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className="btn-secondary mt-6"
                            >
                                选择文件
                            </button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="audio/*"
                                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                                className="hidden"
                            />
                        </div>
                    )}
                </div>

                {/* Error */}
                {uploadMutation.error && (
                    <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-sm max-w-2xl">
                        {(uploadMutation.error as Error).message}
                    </div>
                )}

                {/* Or Record */}
                <div className="text-center mt-6">
                    <p className="text-sm text-gray-500 mb-3">或者</p>
                    <button
                        onClick={() => navigate('/recordings?new=true')}
                        className="btn-primary"
                    >
                        <Mic className="w-4 h-4 mr-2" />
                        直接开始录音
                    </button>
                </div>
            </div>
        </div>
    )
}
