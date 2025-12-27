
import { useNavigate, useLocation } from 'react-router-dom'
import {
    ArrowLeft,
    Download,
    Share2,
    Loader2,
    Check,
    Copy,
    Link
} from 'lucide-react'
import * as Popover from '@radix-ui/react-popover'
import { useState } from 'react'
import { exportApi, shareApi } from '@/api/client'

type ExportFormat = 'markdown' | 'pdf' | 'docx' | 'srt'

interface HeaderSectionProps {
    recording: any
    duration: number
}

export function HeaderSection({ recording, duration }: HeaderSectionProps) {
    const navigate = useNavigate()
    const location = useLocation()
    const [showExportMenu, setShowExportMenu] = useState(false)
    const [isExporting, setIsExporting] = useState(false)
    const [showShareDialog, setShowShareDialog] = useState(false)
    const [shareLink, setShareLink] = useState<string | null>(null)
    const [isCreatingShare, setIsCreatingShare] = useState(false)
    const [shareCopied, setShareCopied] = useState(false)

    // 格式到扩展名的映射
    const formatToExt: Record<ExportFormat, string> = {
        markdown: 'md',
        pdf: 'pdf',
        docx: 'docx',
        srt: 'srt'
    }

    const handleExport = async (format: ExportFormat) => {
        setIsExporting(true)
        try {
            const response = await exportApi.exportRecording(recording.id, format)
            const blob = response.data

            // Verify if the response is actually an error (JSON) disguised as a blob
            if (blob.type === 'application/json' || (blob.size < 500 && format !== 'srt' && format !== 'markdown')) {
                const text = await blob.text()
                try {
                    const errorData = JSON.parse(text)
                    if (errorData.detail) {
                        alert(`导出失败: ${errorData.detail}`)
                        return
                    }
                } catch {
                    // Not valid JSON, proceed as blob
                }
            }

            // Create timestamp string (YYYYMMDD_HHMM)
            const date = new Date(recording.created_at)
            const timestamp = date.getFullYear() +
                String(date.getMonth() + 1).padStart(2, '0') +
                String(date.getDate()).padStart(2, '0') + '_' +
                String(date.getHours()).padStart(2, '0') +
                String(date.getMinutes()).padStart(2, '0')

            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url

            // Sanitize filename: Title + Timestamp
            // Replace all characters that are invalid in filenames on Windows/Mac/Linux
            // Including forward slash, backslash, colon, asterisk, question mark, quotes, angle brackets, pipe
            const titlePrefix = (recording.title || 'recording')
                .replace(/[/\\:*?"<>|]/g, '_')
                .replace(/\s+/g, ' ')  // Normalize whitespace
                .trim()
                .slice(0, 50)  // Limit length

            const extension = formatToExt[format]
            a.download = `${titlePrefix}_${timestamp}.${extension}`

            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)
            setShowExportMenu(false)
        } catch (error: any) {
            console.error('Export failed:', error)

            // Try to extract error message from blob if available
            let errorMessage = '导出失败，请重试'
            if (error.response?.data instanceof Blob) {
                try {
                    const text = await error.response.data.text()
                    const errorData = JSON.parse(text)
                    errorMessage = errorData.detail || errorMessage
                } catch {
                    errorMessage = error.message || errorMessage
                }
            } else {
                errorMessage = error.response?.data?.detail || error.message || errorMessage
            }

            alert(`导出失败: ${errorMessage}`)
        } finally {
            setIsExporting(false)
        }
    }

    const handleCreateShare = async () => {
        setIsCreatingShare(true)
        try {
            const { data } = await shareApi.create({ recording_id: recording.id })
            setShareLink(data.share_url)
        } catch (error) {
            console.error('Share failed:', error)
        } finally {
            setIsCreatingShare(false)
        }
    }

    const handleCopyShare = () => {
        if (shareLink) {
            navigator.clipboard.writeText(shareLink)
            setShareCopied(true)
            setTimeout(() => {
                setShareCopied(false)
                setShowShareDialog(false)
            }, 800)
        }
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}分${secs}秒`
    }

    const handleBack = () => {
        // 使用录音自带的 folder_id
        const folderId = recording.folder_id

        // 根据当前 URL 判断是 /voice-translate 还是 /recordings
        // 注意：RecordingDetailPage 可能挂载在 /recordings/:id 或 /voice-translate/:id
        const isVoiceTranslate = location.pathname.startsWith('/voice-translate')
        const baseUrl = isVoiceTranslate ? '/voice-translate' : '/recordings'

        console.log('[HeaderSection] handleBack:', {
            folderId,
            pathname: location.pathname,
            baseUrl
        })

        // 统一导航策略：
        // 1. 总是回到列表页 -> tab=records
        // 2. 如果有 folderId，带上它 -> folder_id=xxx
        // 3. 如果没有 folderId (默认文件夹)，不带 folder_id 参数，但 tab=records 会确保显示列表而非录音页
        const params = new URLSearchParams({
            tab: 'records'
        })

        if (folderId) {
            params.set('folder_id', folderId)
        }

        const url = `${baseUrl}?${params.toString()}`
        navigate(url)
    }

    return (
        <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
                <button
                    onClick={handleBack}
                    className="p-2 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-full transition-colors border border-transparent hover:border-brand-100/50"
                >
                    <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                </button>
                <div>
                    <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                        {recording.title}
                    </h1>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{new Date(recording.created_at).toLocaleString()}</span>
                        <span>·</span>
                        <span>{formatTime(duration || recording.duration_seconds)}</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <div className="relative">
                    <button
                        onClick={() => setShowExportMenu(!showExportMenu)}
                        className="p-2 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg text-gray-500 transition-colors border border-transparent hover:border-brand-100/50"
                        title="导出"
                    >
                        <Download className="w-5 h-5" />
                    </button>

                    {showExportMenu && (
                        <div className="absolute top-full right-0 mt-2 w-48 bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-brand-100 dark:border-brand-800 z-50 overflow-hidden">
                            <div className="p-1">
                                {(['markdown', 'docx', 'pdf', 'srt'] as ExportFormat[]).map((format) => (
                                    <button
                                        key={format}
                                        onClick={() => handleExport(format)}
                                        disabled={isExporting}
                                        className="w-full text-left px-4 py-2 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-300 flex items-center justify-between"
                                    >
                                        <span className="uppercase">{format}</span>
                                        {isExporting && <Loader2 className="w-3 h-3 animate-spin" />}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <Popover.Root open={showShareDialog} onOpenChange={setShowShareDialog}>
                    <Popover.Trigger asChild>
                        <button
                            className="p-2 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg text-gray-500 transition-colors border border-transparent hover:border-brand-100/50"
                            title="分享"
                        >
                            <Share2 className="w-5 h-5" />
                        </button>
                    </Popover.Trigger>

                    <Popover.Portal>
                        <Popover.Content
                            className="w-72 bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-brand-100 dark:border-brand-800 z-50 p-4 animate-in fade-in zoom-in duration-200"
                            sideOffset={8}
                            align="end"
                        >
                            <h3 className="text-sm font-semibold mb-3">分享录音</h3>
                            {shareLink ? (
                                <div className="flex items-center gap-2">
                                    <input
                                        readOnly
                                        value={shareLink}
                                        className="flex-1 text-xs bg-brand-50 dark:bg-gray-800 border border-brand-100 dark:border-brand-800 rounded p-2 outline-none"
                                    />
                                    <button
                                        onClick={handleCopyShare}
                                        className="p-2 hover:bg-brand-100 dark:hover:bg-gray-800 rounded-lg border border-transparent hover:border-brand-200"
                                    >
                                        {shareCopied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={handleCreateShare}
                                    disabled={isCreatingShare}
                                    className="w-full btn-primary py-2 text-sm"
                                >
                                    {isCreatingShare ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Link className="w-4 h-4 mr-2" />}
                                    生成分享链接
                                </button>
                            )}
                            <Popover.Arrow className="fill-white dark:fill-gray-900" />
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>
            </div>
        </div>
    )
}
