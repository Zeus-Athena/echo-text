/**
 * Dictionary Page
 * 词典页 - 优化版：实时查询、同义词反义词、生词本删除、单词联想
 */
import { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { translateApi } from '@/api/client'
import { useDebounce } from '@/hooks/useDebounce'
import {
    Search,
    Volume2,
    BookmarkPlus,
    Loader2,
    X,
    Trash2,
    Check,
    Bookmark,
} from 'lucide-react'

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

interface VocabularyItem {
    id: string
    word: string
    language?: string
}

export default function DictionaryPage() {
    const [searchWord, setSearchWord] = useState('')
    const [showSuggestions, setShowSuggestions] = useState(false)
    const [addedToVocab, setAddedToVocab] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    const queryClient = useQueryClient()

    // Debounce search word for auto-query
    const debouncedSearchWord = useDebounce(searchWord, 600)

    // Dictionary query - now triggered by debounced value
    const { data: result, isLoading } = useQuery({
        queryKey: ['dictionary', debouncedSearchWord],
        queryFn: () => translateApi.lookupWord(debouncedSearchWord.trim()),
        select: (res) => res.data as DictionaryResult,
        enabled: !!debouncedSearchWord.trim(),
    })

    const { data: history } = useQuery({
        queryKey: ['dictionary-history'],
        queryFn: () => translateApi.getDictionaryHistory(20),
        select: (res) => res.data as string[],
    })

    const { data: vocabulary } = useQuery({
        queryKey: ['vocabulary'],
        queryFn: () => translateApi.getVocabulary(),
        select: (res) => res.data as VocabularyItem[],
    })

    // Word suggestions based on history
    const suggestions = useMemo(() => {
        if (!searchWord.trim() || !history || !Array.isArray(history)) return []
        const query = searchWord.toLowerCase()
        return history
            .filter((word: string) => word.toLowerCase().startsWith(query) && word.toLowerCase() !== query)
            .slice(0, 5)
    }, [searchWord, history])

    // Check if current word is in vocabulary
    const isInVocabulary = useMemo(() => {
        if (!result?.word || !vocabulary) return false
        return vocabulary.some((item: VocabularyItem) => item.word.toLowerCase() === result.word.toLowerCase())
    }, [result?.word, vocabulary])

    // Add to vocabulary mutation
    const addToVocab = useMutation({
        mutationFn: (word: string) => translateApi.addToVocabulary({ word }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
            setAddedToVocab(true)
            setTimeout(() => setAddedToVocab(false), 1500)
        },
    })

    // Remove from vocabulary mutation
    const removeFromVocab = useMutation({
        mutationFn: (word: string) => translateApi.removeFromVocabulary(word),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
        },
    })

    // TTS mutation
    const ttsMutation = useMutation({
        mutationFn: (text: string) => translateApi.tts({ text }),
        onSuccess: (res) => {
            const audioUrl = URL.createObjectURL(res.data)
            new Audio(audioUrl).play()
        },
    })

    // Invalidate history query when a new search result is returned
    useEffect(() => {
        if (result?.word) {
            queryClient.invalidateQueries({ queryKey: ['dictionary-history'] })
        }
    }, [result?.word, queryClient])

    const handleSelectSuggestion = (word: string) => {
        setSearchWord(word)
        setShowSuggestions(false)
        // Also trigger search immediately for suggestions
        queryClient.invalidateQueries({ queryKey: ['dictionary', word] })
    }

    const handleClearSearch = () => {
        setSearchWord('')
        inputRef.current?.focus()
    }

    // Close suggestions when clicking outside
    useEffect(() => {
        const handleClickOutside = () => setShowSuggestions(false)
        document.addEventListener('click', handleClickOutside)
        return () => document.removeEventListener('click', handleClickOutside)
    }, [])

    return (
        <div className="px-4 lg:px-8 py-6 max-w-7xl mx-auto">
            {/* Search */}
            <div className="relative mb-6">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        ref={inputRef}
                        type="text"
                        placeholder="输入单词查询..."
                        value={searchWord}
                        onChange={(e) => {
                            setSearchWord(e.target.value)
                            setShowSuggestions(true)
                        }}
                        onFocus={() => setShowSuggestions(true)}
                        onClick={(e) => e.stopPropagation()}
                        className="input pl-10 pr-10"
                    />
                    {searchWord && (
                        <button
                            onClick={handleClearSearch}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-brand-50 dark:hover:bg-gray-700 rounded-full transition-colors"
                        >
                            <X className="w-4 h-4 text-gray-400" />
                        </button>
                    )}
                </div>

                {/* Suggestions Dropdown */}
                {showSuggestions && suggestions.length > 0 && (
                    <div
                        className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-900 border border-brand-200 dark:border-brand-800 rounded-lg shadow-xl shadow-brand-500/10"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {suggestions.map((word: string) => (
                            <button
                                key={word}
                                onClick={() => handleSelectSuggestion(word)}
                                className="w-full px-4 py-2 text-left hover:bg-brand-50 dark:hover:bg-gray-800 first:rounded-t-lg last:rounded-b-lg border-b border-brand-50 dark:border-brand-900/10 last:border-0"
                            >
                                {word}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
                {/* Result */}
                <div className="lg:col-span-2">
                    {isLoading ? (
                        <div className="card p-12 text-center">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-500" />
                            <p className="mt-2 text-gray-500">查询中...</p>
                        </div>
                    ) : result ? (
                        <div className="card p-6">
                            {/* Word Header */}
                            <div className="flex items-start justify-between mb-4">
                                <div>
                                    <h2 className="text-2xl font-bold">{result.word}</h2>
                                    {result.phonetic && (
                                        <p className="text-gray-500 mt-1">{result.phonetic}</p>
                                    )}
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => ttsMutation.mutate(result.word)}
                                        disabled={ttsMutation.isPending}
                                        className="p-2 hover:bg-brand-50 dark:hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50 border border-transparent hover:border-brand-100/50"
                                        title="朗读"
                                    >
                                        <Volume2 className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                                    </button>
                                    <button
                                        onClick={() => addToVocab.mutate(result.word)}
                                        disabled={addToVocab.isPending || isInVocabulary}
                                        className={`p-2 rounded-lg transition-colors border ${isInVocabulary || addedToVocab
                                            ? 'bg-green-100 border-green-200 dark:bg-green-900/30 dark:border-green-800 text-green-600'
                                            : 'border-transparent hover:bg-brand-50 hover:border-brand-100 dark:hover:bg-gray-800'
                                            }`}
                                        title={isInVocabulary ? '已在生词本' : '加入生词本'}
                                    >
                                        {isInVocabulary || addedToVocab ? (
                                            <Bookmark className="w-5 h-5 fill-current" />
                                        ) : (
                                            <BookmarkPlus className="w-5 h-5" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Definitions */}
                            <div className="space-y-4">
                                {result.definitions?.map((def, i) => (
                                    <div key={i} className="border-l-2 border-brand-500 pl-4">
                                        <span className="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase">
                                            {def.part_of_speech}
                                        </span>
                                        <p className="mt-1">{def.definition}</p>
                                        {def.example && (
                                            <p className="text-sm text-gray-500 mt-2 italic">
                                                "{def.example}"
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Phrases */}
                            {result.phrases && result.phrases.length > 0 && (
                                <div className="mt-6">
                                    <h3 className="text-sm font-medium text-brand-700/60 dark:text-brand-300/60 mb-2">常用词组</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {result.phrases.map((phrase, i) => (
                                            <span
                                                key={i}
                                                className="px-2 py-1 bg-brand-50 dark:bg-gray-800 rounded text-sm border border-brand-100/50 dark:border-brand-900/30"
                                            >
                                                {phrase}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Synonyms */}
                            {result.synonyms && result.synonyms.length > 0 && (
                                <div className="mt-6">
                                    <h3 className="text-sm font-medium text-brand-700/60 dark:text-brand-300/60 mb-2">同义词</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {result.synonyms.map((word, i) => (
                                            <button
                                                key={i}
                                                onClick={() => setSearchWord(word)}
                                                className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-sm hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                            >
                                                {word}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Antonyms */}
                            {result.antonyms && result.antonyms.length > 0 && (
                                <div className="mt-6">
                                    <h3 className="text-sm font-medium text-brand-700/60 dark:text-brand-300/60 mb-2">反义词</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {result.antonyms.map((word, i) => (
                                            <button
                                                key={i}
                                                onClick={() => setSearchWord(word)}
                                                className="px-2 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded text-sm hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors"
                                            >
                                                {word}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="card p-12 text-center text-gray-500">
                            <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
                            <p>输入单词开始查询</p>
                            <p className="text-sm mt-1">支持实时查询，输入即查</p>
                        </div>
                    )}
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Recent */}
                    <div className="card">
                        <div className="p-4 border-b border-brand-100 dark:border-brand-800 flex items-center justify-between bg-brand-50/10 dark:bg-gray-800/50">
                            <h3 className="font-medium text-brand-800 dark:text-brand-200">
                                最近查询
                                {history && Array.isArray(history) && history.length > 0 && (
                                    <span className="ml-2 text-xs text-brand-400">({history.length})</span>
                                )}
                            </h3>
                            {history && Array.isArray(history) && history.length > 0 && (
                                <button
                                    onClick={() => {
                                        // Clear by invalidating cache (frontend only)
                                        queryClient.setQueryData(['dictionary-history'], [])
                                    }}
                                    className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                                    title="清空历史"
                                >
                                    清空
                                </button>
                            )}
                        </div>
                        <div className="p-2 max-h-48 overflow-y-auto">
                            {history && Array.isArray(history) && history.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                    {history.slice(0, 15).map((word: string, index: number) => (
                                        <button
                                            key={`${word}-${index}`}
                                            onClick={() => setSearchWord(word)}
                                            className="px-2 py-1 text-sm bg-brand-50 dark:bg-gray-800/50 hover:bg-brand-100 dark:hover:bg-gray-800 rounded transition-colors border border-brand-100/50 dark:border-brand-900/30 text-brand-700 dark:text-brand-300"
                                        >
                                            {word}
                                        </button>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-gray-500 p-2 text-center">暂无记录</p>
                            )}
                        </div>
                    </div>

                    {/* Vocabulary */}
                    <div className="card">
                        <h3 className="p-4 border-b border-brand-100 dark:border-brand-800 font-medium text-brand-800 dark:text-brand-200 bg-brand-50/10 dark:bg-gray-800/50">
                            生词本 ({vocabulary?.length || 0})
                        </h3>
                        <div className="p-2 max-h-64 overflow-y-auto">
                            {vocabulary && vocabulary.length > 0 ? (
                                <div className="space-y-1">
                                    {vocabulary.map((item: VocabularyItem) => (
                                        <div
                                            key={item.id}
                                            className="flex items-center justify-between group px-2 py-1 rounded hover:bg-brand-50 dark:hover:bg-gray-800/50 border border-transparent hover:border-brand-100/50 transition-colors"
                                        >
                                            <button
                                                onClick={() => setSearchWord(item.word)}
                                                className="text-sm text-brand-600 dark:text-brand-400 hover:underline font-medium"
                                            >
                                                {item.word}
                                            </button>
                                            <button
                                                onClick={() => removeFromVocab.mutate(item.word)}
                                                className="p-1 opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 rounded transition-all"
                                                title="从生词本移除"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-gray-500 p-2">暂无生词</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
