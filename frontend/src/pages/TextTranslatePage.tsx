/**
 * Text Translate Page
 * 文本翻译页 - 优化版：实时翻译、词典模式、历史记录、风格选择、文件上传
 */
import { useState, useRef, useEffect, ChangeEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { translateApi } from '@/api/client'
import { useDebounce } from '@/hooks/useDebounce'
import {
    Languages,
    ArrowRightLeft,
    Volume2,
    Copy,
    Loader2,
    X,
    History,
    Book,
    Check,
    Upload,
    FileText,
    Sparkles,
} from 'lucide-react'

const LANGUAGES = [
    { code: 'zh', name: '中文' },
    { code: 'en', name: 'English' },
    { code: 'ja', name: '日本語' },
    { code: 'ko', name: '한국어' },
]

const STYLES = [
    { code: 'standard', name: '标准', icon: '📝' },
    { code: 'formal', name: '正式', icon: '👔' },
    { code: 'casual', name: '口语化', icon: '💬' },
]

interface DictionaryResult {
    word: string
    phonetic?: string
    definitions?: Array<{
        part_of_speech: string
        definition: string
        example?: string
    }>
    phrases?: string[]
    synonyms?: string[]
    antonyms?: string[]
}

interface TranslationHistoryItem {
    id: string
    source_text: string
    translated_text: string
    source_lang: string
    target_lang: string
    created_at: string
}

// Parse SRT file content to extract text
const parseSRT = (content: string): string => {
    const lines = content.split('\n')
    const textLines: string[] = []
    let isTextLine = false

    for (const line of lines) {
        const trimmed = line.trim()

        // Skip empty lines and sequence numbers
        if (!trimmed || /^\d+$/.test(trimmed)) {
            isTextLine = false
            continue
        }

        // Skip timestamp lines (e.g., 00:00:01,000 --> 00:00:04,000)
        if (/^\d{2}:\d{2}:\d{2}[,.:]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.:]\d{3}$/.test(trimmed)) {
            isTextLine = true
            continue
        }

        // This is a subtitle text line
        if (isTextLine || (!trimmed.includes('-->') && !/^\d+$/.test(trimmed))) {
            textLines.push(trimmed)
        }
    }

    return textLines.join('\n')
}

export default function TextTranslatePage() {
    const [sourceText, setSourceText] = useState('')
    const [translatedText, setTranslatedText] = useState('')
    const [sourceLang, setSourceLang] = useState('zh')
    const [targetLang, setTargetLang] = useState('en')
    const [style, setStyle] = useState('standard')
    const [dictionaryResult, setDictionaryResult] = useState<DictionaryResult | null>(null)
    const [showHistory, setShowHistory] = useState(false)
    const [copied, setCopied] = useState<'source' | 'target' | null>(null)
    const [uploadedFileName, setUploadedFileName] = useState<string | null>(null)

    // Debounce source text for auto-translate
    const debouncedSourceText = useDebounce(sourceText, 800)

    // File input ref
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Single audio instance to prevent overlapping
    const audioRef = useRef<HTMLAudioElement | null>(null)
    const audioUrlRef = useRef<string | null>(null)

    // Check if input is a single word (for dictionary mode)
    const isSingleWord = (text: string) => {
        const trimmed = text.trim()
        // Single word: no spaces, or Chinese single character
        return trimmed.length > 0 && !trimmed.includes(' ') && trimmed.length <= 30
    }

    // Translation history query
    const historyQuery = useQuery({
        queryKey: ['translationHistory'],
        queryFn: async () => {
            const res = await translateApi.getHistory(20)
            return res.data as TranslationHistoryItem[]
        },
        enabled: showHistory,
    })

    // Translate mutation
    const translateMutation = useMutation({
        mutationFn: () =>
            translateApi.translateText({
                text: sourceText,
                source_lang: sourceLang,
                target_lang: targetLang,
                style: style,
            }),
        onSuccess: (res) => {
            setTranslatedText(res.data.translated_text)
        },
    })

    // Dictionary lookup mutation
    const dictionaryMutation = useMutation({
        mutationFn: (word: string) => translateApi.lookupWord(word, sourceLang),
        onSuccess: (res) => {
            setDictionaryResult(res.data)
        },
        onError: () => {
            setDictionaryResult(null)
        },
    })

    // TTS mutation
    const ttsMutation = useMutation({
        mutationFn: (text: string) => translateApi.tts({ text }),
        onSuccess: (res) => {
            // Stop any existing audio
            if (audioRef.current) {
                audioRef.current.pause()
                audioRef.current.currentTime = 0
            }

            // Clean up previous URL
            if (audioUrlRef.current) {
                URL.revokeObjectURL(audioUrlRef.current)
            }

            // Create new audio and play
            const audioUrl = URL.createObjectURL(res.data)
            audioUrlRef.current = audioUrl
            audioRef.current = new Audio(audioUrl)
            audioRef.current.play()
        },
    })

    // Auto-translate when debounced text changes
    useEffect(() => {
        if (debouncedSourceText.trim()) {
            translateMutation.mutate()

            // If single word, also lookup dictionary
            if (isSingleWord(debouncedSourceText)) {
                dictionaryMutation.mutate(debouncedSourceText.trim())
            } else {
                setDictionaryResult(null)
            }
        } else {
            setTranslatedText('')
            setDictionaryResult(null)
        }
    }, [debouncedSourceText, sourceLang, targetLang, style])

    const handleTTS = (text: string) => {
        // If already playing, stop and restart
        if (audioRef.current && !audioRef.current.paused) {
            audioRef.current.pause()
            audioRef.current.currentTime = 0
            audioRef.current.play()
            return
        }
        ttsMutation.mutate(text)
    }

    const swapLanguages = () => {
        setSourceLang(targetLang)
        setTargetLang(sourceLang)
        setSourceText(translatedText)
        setTranslatedText(sourceText)
    }

    const handleCopy = async (text: string, type: 'source' | 'target') => {
        await navigator.clipboard.writeText(text)
        setCopied(type)
        setTimeout(() => setCopied(null), 1500)
    }

    const clearSourceText = () => {
        setSourceText('')
        setTranslatedText('')
        setDictionaryResult(null)
        setUploadedFileName(null)
    }

    const loadFromHistory = (item: TranslationHistoryItem) => {
        setSourceText(item.source_text)
        setTranslatedText(item.translated_text)
        setSourceLang(item.source_lang)
        setTargetLang(item.target_lang)
        setShowHistory(false)
    }

    // Handle file upload
    const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        const fileName = file.name.toLowerCase()
        const isSRT = fileName.endsWith('.srt')
        const isTXT = fileName.endsWith('.txt')

        if (!isSRT && !isTXT) {
            alert('仅支持 .txt 和 .srt 文件')
            return
        }

        try {
            const content = await file.text()
            let text = content

            if (isSRT) {
                text = parseSRT(content)
            }

            setSourceText(text)
            setUploadedFileName(file.name)
        } catch {
            alert('文件读取失败')
        }

        // Reset input so same file can be uploaded again
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const triggerFileUpload = () => {
        fileInputRef.current?.click()
    }

    return (
        <div className="px-4 lg:px-8 py-6 max-w-7xl mx-auto">
            {/* Language & Style Selector */}
            <div className="flex flex-wrap items-center gap-4 mb-4">
                <select
                    value={sourceLang}
                    onChange={(e) => setSourceLang(e.target.value)}
                    className="input w-32"
                >
                    {LANGUAGES.map((lang) => (
                        <option key={lang.code} value={lang.code}>
                            {lang.name}
                        </option>
                    ))}
                </select>

                <button
                    onClick={swapLanguages}
                    className="p-2 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg transition-colors border border-transparent hover:border-brand-100"
                    title="交换语言"
                >
                    <ArrowRightLeft className="w-5 h-5 text-gray-500" />
                </button>

                <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="input w-32"
                >
                    {LANGUAGES.map((lang) => (
                        <option key={lang.code} value={lang.code}>
                            {lang.name}
                        </option>
                    ))}
                </select>

                {/* Style Selector */}
                <div className="flex items-center gap-1 ml-2 p-1 bg-brand-50/50 dark:bg-gray-800 rounded-lg border border-brand-100/50">
                    {STYLES.map((s) => (
                        <button
                            key={s.code}
                            onClick={() => setStyle(s.code)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${style === s.code
                                ? 'bg-white dark:bg-gray-700 shadow-sm text-brand-600 dark:text-brand-400 font-medium'
                                : 'hover:bg-brand-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400'
                                }`}
                            title={s.name}
                        >
                            <span>{s.icon}</span>
                            <span className="hidden sm:inline">{s.name}</span>
                        </button>
                    ))}
                </div>

                <div className="flex-1" />

                {/* File Upload */}
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.srt"
                    onChange={handleFileUpload}
                    className="hidden"
                />
                <button
                    onClick={triggerFileUpload}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-brand-50 dark:hover:bg-gray-800 transition-colors border border-transparent hover:border-brand-100"
                    title="上传文件 (.txt, .srt)"
                >
                    <Upload className="w-4 h-4 text-gray-500" />
                    <span className="text-sm hidden sm:inline">上传</span>
                </button>

                {/* History Toggle */}
                <button
                    onClick={() => setShowHistory(!showHistory)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors border ${showHistory
                        ? 'bg-brand-100 border-brand-200 text-brand-600 dark:bg-brand-900/30 dark:border-brand-800 dark:text-brand-400'
                        : 'border-transparent hover:bg-brand-50 hover:border-brand-100 text-gray-600'
                        }`}
                >
                    <History className="w-4 h-4" />
                    <span className="text-sm hidden sm:inline">历史</span>
                </button>
            </div>

            {/* Uploaded File Indicator */}
            {uploadedFileName && (
                <div className="mb-4 flex items-center gap-2 text-sm text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 px-3 py-2 rounded-lg border border-brand-100">
                    <FileText className="w-4 h-4" />
                    <span>已加载: {uploadedFileName}</span>
                    <button
                        onClick={() => setUploadedFileName(null)}
                        className="ml-auto hover:text-brand-800 dark:hover:text-brand-300"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Translation Boxes */}
            <div className="grid lg:grid-cols-2 gap-4">
                {/* Source */}
                <div className="card">
                    <div className="p-4 border-b border-brand-100 dark:border-brand-800/60 flex items-center justify-between bg-brand-50/10 dark:bg-gray-800/50">
                        <span className="text-sm font-medium text-brand-700 dark:text-brand-300">原文</span>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => handleTTS(sourceText)}
                                disabled={!sourceText || ttsMutation.isPending}
                                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded disabled:opacity-50 transition-colors"
                                title="朗读"
                            >
                                <Volume2 className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => handleCopy(sourceText, 'source')}
                                disabled={!sourceText}
                                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded disabled:opacity-50 transition-colors"
                                title="复制"
                            >
                                {copied === 'source' ? (
                                    <Check className="w-4 h-4 text-green-500" />
                                ) : (
                                    <Copy className="w-4 h-4" />
                                )}
                            </button>
                        </div>
                    </div>
                    <div className="relative">
                        <textarea
                            value={sourceText}
                            onChange={(e) => setSourceText(e.target.value)}
                            placeholder="输入要翻译的文本，或上传文件..."
                            className="w-full h-64 p-4 resize-none focus:outline-none bg-transparent"
                        />
                        {sourceText && (
                            <button
                                onClick={clearSourceText}
                                className="absolute top-3 right-3 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
                                title="清除"
                            >
                                <X className="w-4 h-4 text-gray-400" />
                            </button>
                        )}
                    </div>
                    <div className="p-3 border-t border-brand-100 dark:border-brand-800 flex justify-between items-center">
                        <span className="text-xs text-gray-500">{sourceText.length} 字</span>
                        <button
                            onClick={() => translateMutation.mutate()}
                            disabled={!sourceText || translateMutation.isPending}
                            className="btn-primary"
                        >
                            {translateMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <>
                                    <Languages className="w-4 h-4 mr-2" />
                                    翻译
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Target */}
                <div className="card bg-brand-50/5 dark:bg-gray-800/50 border-brand-200 dark:border-brand-800">
                    <div className="p-4 border-b border-brand-200/50 dark:border-brand-700 flex items-center justify-between bg-brand-50/30 dark:bg-gray-800/80">
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-brand-700 dark:text-brand-300">译文</span>
                            {style !== 'standard' && (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 flex items-center gap-1">
                                    <Sparkles className="w-3 h-3" />
                                    {STYLES.find(s => s.code === style)?.name}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => handleTTS(translatedText)}
                                disabled={!translatedText || ttsMutation.isPending}
                                className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded disabled:opacity-50 transition-colors"
                                title="朗读"
                            >
                                <Volume2 className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => handleCopy(translatedText, 'target')}
                                disabled={!translatedText}
                                className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded disabled:opacity-50 transition-colors"
                                title="复制"
                            >
                                {copied === 'target' ? (
                                    <Check className="w-4 h-4 text-green-500" />
                                ) : (
                                    <Copy className="w-4 h-4" />
                                )}
                            </button>
                        </div>
                    </div>
                    <div className="h-64 p-4 overflow-y-auto">
                        {translateMutation.isPending ? (
                            <div className="flex items-center gap-2 text-gray-400">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>翻译中...</span>
                            </div>
                        ) : translatedText ? (
                            <p className="whitespace-pre-wrap">{translatedText}</p>
                        ) : (
                            <span className="text-gray-400">翻译结果将显示在这里...</span>
                        )}
                    </div>
                    <div className="p-3 border-t border-brand-100 dark:border-brand-700">
                        <span className="text-xs text-gray-500">{translatedText.length} 字</span>
                    </div>
                </div>
            </div>

            {/* Dictionary Card (when single word detected) */}
            {dictionaryResult && (
                <div className="mt-4 card p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Book className="w-5 h-5 text-primary-500" />
                        <h3 className="font-medium">词典</h3>
                    </div>
                    <div className="space-y-3">
                        <div className="flex items-baseline gap-3">
                            <span className="text-lg font-semibold">{dictionaryResult.word}</span>
                            {dictionaryResult.phonetic && (
                                <span className="text-gray-500">{dictionaryResult.phonetic}</span>
                            )}
                        </div>
                        {dictionaryResult.definitions?.map((def, i) => (
                            <div key={i} className="pl-4 border-l-2 border-primary-200 dark:border-primary-800">
                                <span className="text-sm text-primary-600 dark:text-primary-400">
                                    {def.part_of_speech}
                                </span>
                                <p className="text-sm mt-1">{def.definition}</p>
                                {def.example && (
                                    <p className="text-sm text-gray-500 mt-1 italic">例: {def.example}</p>
                                )}
                            </div>
                        ))}
                        {dictionaryResult.synonyms && dictionaryResult.synonyms.length > 0 && (
                            <div className="text-sm">
                                <span className="text-gray-500">同义词: </span>
                                {dictionaryResult.synonyms.join(', ')}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* History Panel */}
            {showHistory && (
                <div className="mt-4 card">
                    <div className="p-4 border-b border-brand-100 dark:border-brand-800">
                        <h3 className="font-medium text-brand-700 dark:text-brand-300">最近翻译</h3>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                        {historyQuery.isLoading ? (
                            <div className="p-4 text-center text-gray-400">
                                <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                            </div>
                        ) : historyQuery.data?.length === 0 ? (
                            <div className="p-4 text-center text-gray-400">暂无翻译历史</div>
                        ) : (
                            <div className="divide-y divide-brand-50 dark:divide-brand-900/30">
                                {historyQuery.data?.map((item) => (
                                    <button
                                        key={item.id}
                                        onClick={() => loadFromHistory(item)}
                                        className="w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                                    >
                                        <p className="text-sm truncate">{item.source_text}</p>
                                        <p className="text-xs text-gray-500 truncate mt-1">
                                            → {item.translated_text}
                                        </p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
