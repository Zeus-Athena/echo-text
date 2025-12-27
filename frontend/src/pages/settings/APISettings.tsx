
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userApi, configApi } from '@/api/client'
import { useToast } from '@/components/Toast'
import { Save, Loader2, Eye, EyeOff, RefreshCw, Wallet, Settings2, MessageSquareCode, Zap, CheckCircle2, XCircle, X } from 'lucide-react'
import AIPromptsSettings from './AIPromptsSettings'

// Balance Card Component
function BalanceCard({
    serviceType,
    provider
}: {
    serviceType: 'llm' | 'stt';
    provider: string
}) {
    const [isRefreshing, setIsRefreshing] = useState(false)

    const { data, refetch, isLoading, isError } = useQuery({
        queryKey: ['balance', serviceType, provider],
        queryFn: () => userApi.getBalance(serviceType, provider),
        select: (res) => res.data,
        enabled: !!provider,
        staleTime: 1000 * 60 * 5, // 5 minutes
        refetchOnWindowFocus: false,
    })

    const handleRefresh = async () => {
        setIsRefreshing(true)
        await refetch()
        setIsRefreshing(false)
    }

    // Supported providers for balance check
    const supportedProviders = serviceType === 'llm'
        ? ['siliconflow']
        : ['deepgram', 'siliconflow']

    const isSupported = supportedProviders.includes(provider.toLowerCase())

    if (!isSupported) {
        return (
            <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                    <Wallet className="w-4 h-4" />
                    <span>余额查询暂不支持 {provider}</span>
                </div>
            </div>
        )
    }

    return (
        <div className="mt-4 p-4 bg-transparent rounded-lg border border-brand-200 dark:border-brand-800">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Wallet className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    <span className="font-medium text-gray-700 dark:text-gray-300">账户余额</span>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={isLoading || isRefreshing}
                    className="p-1.5 hover:bg-white dark:hover:bg-gray-700 rounded-md transition-colors"
                    title="刷新余额"
                >
                    <RefreshCw className={`w-4 h-4 text-gray-500 ${isRefreshing ? 'animate-spin' : ''}`} />
                </button>
            </div>
            <div className="mt-2">
                {isLoading ? (
                    <div className="flex items-center gap-2 text-gray-500">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">加载中...</span>
                    </div>
                ) : isError || data?.error ? (
                    <div className="text-red-500 text-sm">
                        {data?.error || '查询失败'}
                    </div>
                ) : data?.message ? (
                    <div className="text-gray-500 text-sm">
                        {data.message}
                    </div>
                ) : data?.balance !== undefined ? (
                    <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {data.currency === 'CNY' ? '¥' : '$'}
                        {typeof data.balance === 'number' ? data.balance.toFixed(2) : data.balance}
                    </div>
                ) : null}
            </div>
        </div>
    )
}

// Test Result Interface
interface TestResult {
    status: 'success' | 'error' | null;
    message: string;
    latency?: number;
}

// Inline Test Result Display Component
function TestResultDisplay({ result, onClear }: { result: TestResult, onClear: () => void }) {
    if (!result.status) return null

    const isSuccess = result.status === 'success'

    return (
        <div className={`mb-4 flex items-center justify-between p-3 rounded-lg border ${isSuccess
            ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400'
            : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400'
            }`}>
            <div className="flex items-center gap-2 text-sm font-medium">
                {isSuccess ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                <span>
                    {result.message}
                    {result.latency !== undefined && ` (${result.latency}ms)`}
                </span>
            </div>
            <button
                onClick={onClear}
                className="p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-md transition-colors"
                title="清除"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    )
}

// Provider configurations
const LLM_PROVIDERS = {
    SiliconFlow: {
        base_url: 'https://api.siliconflow.cn/v1',
        models: [
            { id: 'deepseek-ai/DeepSeek-V3', name: 'DeepSeek-V3 (最新)', pricing: '¥1/M tokens' },
            { id: 'Pro/deepseek-ai/DeepSeek-V3', name: 'DeepSeek-V3 Pro', pricing: '¥2/M tokens' },
            { id: 'deepseek-ai/DeepSeek-R1', name: 'DeepSeek-R1 (推理)', pricing: '¥4/M tokens' },
            { id: 'deepseek-ai/DeepSeek-V2.5', name: 'DeepSeek-V2.5', pricing: '¥0.5/M tokens' },
            { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', name: 'DeepSeek-R1-7B (免费)', pricing: '免费' },
        ]
    },
    GROQ: {
        base_url: 'https://api.groq.com/openai/v1',
        models: [
            { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B Versatile', pricing: '免费' },
        ]
    }
}

const STT_PROVIDERS = {
    SiliconFlow: {
        base_url: 'https://api.siliconflow.cn/v1',
        models: [
            { id: 'FunAudioLLM/SenseVoiceSmall', name: 'SenseVoice Small', pricing: '¥0.01/次', accuracy: '⭐⭐⭐⭐⭐' },
            { id: 'TeleAI/TeleSpeechASR', name: 'TeleSpeech ASR', pricing: '¥0.01/次', accuracy: '⭐⭐⭐⭐' },
        ]
    },
    GROQ: {
        base_url: 'https://api.groq.com/openai/v1',
        models: [
            { id: 'whisper-large-v3-turbo', name: 'Whisper Large V3 Turbo', pricing: '免费', accuracy: '⭐⭐⭐⭐⭐' },
            { id: 'whisper-large-v3', name: 'Whisper Large V3', pricing: '免费', accuracy: '⭐⭐⭐⭐⭐' },
            { id: 'distil-whisper-large-v3-en', name: 'Distil Whisper (English)', pricing: '免费', accuracy: '⭐⭐⭐⭐' },
        ]
    },
    OpenAI: {
        base_url: 'https://api.openai.com/v1',
        models: [
            { id: 'whisper-1', name: 'Whisper-1', pricing: '$0.006/分钟', accuracy: '⭐⭐⭐⭐⭐' },
        ]
    },
    Deepgram: {
        base_url: 'https://api.deepgram.com/v1',
        models: [
            { id: 'nova-3-general', name: 'Nova-3 General', pricing: '$0.0059/分钟', accuracy: '⭐⭐⭐⭐⭐' },
            { id: 'flux-general-en', name: 'Flux (英文)', pricing: '$0.0077/分钟', accuracy: '⭐⭐⭐⭐⭐' },
            { id: 'nova-2-general', name: 'Nova-2 General', pricing: '$0.0043/分钟', accuracy: '⭐⭐⭐⭐' },
        ]
    }
}

export function APISettings() {
    const [activeTab, setActiveTab] = useState<'connection' | 'prompts'>('connection')
    const queryClient = useQueryClient()
    const toast = useToast()

    // Test Results State
    const [llmTestResult, setLlmTestResult] = useState<TestResult>({ status: null, message: '' })
    const [sttTestResult, setSttTestResult] = useState<TestResult>({ status: null, message: '' })
    const [ttsTestResult, setTtsTestResult] = useState<TestResult>({ status: null, message: '' })

    const { data: config, isLoading } = useQuery({
        queryKey: ['user-config'],
        queryFn: () => userApi.getConfig(),
        select: (res) => res.data,
        refetchOnWindowFocus: false,
    })

    const [llm, setLLM] = useState({
        provider: 'GROQ',
        api_key: '',
        base_url: 'https://api.groq.com/openai/v1',
        model: 'llama-3.3-70b-versatile',
        keys: {} as Record<string, string | null>
    })
    const [stt, setSTT] = useState({
        provider: 'GROQ',
        api_key: '',
        base_url: 'https://api.groq.com/openai/v1',
        model: 'whisper-large-v3-turbo',
        keys: {} as Record<string, string | null>
    })
    const [tts, setTTS] = useState({ provider: 'edge', voice: 'zh-CN-XiaoxiaoNeural' })

    // Password visibility state
    const [showLLMKey, setShowLLMKey] = useState(false)
    const [showSTTKey, setShowSTTKey] = useState(false)

    // Helper to get key name for provider (normalize to match backend keys)
    const getKeyName = (provider: string) => provider.toLowerCase()

    // Handle LLM provider change
    const handleLLMProviderChange = (provider: string) => {
        if (provider === llm.provider) return

        const config = LLM_PROVIDERS[provider as keyof typeof LLM_PROVIDERS]
        if (config) {
            const keyName = getKeyName(provider)
            const savedKey = llm.keys[keyName] || ''

            setLLM({
                ...llm,
                provider,
                api_key: savedKey,
                base_url: config.base_url,
                model: config.models[0].id
            })
        }
    }

    // Handle STT provider change
    const handleSTTProviderChange = (provider: string) => {
        if (provider === stt.provider) return

        const config = STT_PROVIDERS[provider as keyof typeof STT_PROVIDERS]
        if (config) {
            const keyName = getKeyName(provider)
            const savedKey = stt.keys[keyName] || ''

            setSTT({
                ...stt,
                provider,
                api_key: savedKey,
                base_url: config.base_url,
                model: config.models[0].id
            })
        }
    }

    // Handle LLM Key Change
    const handleLLMKeyChange = (val: string) => {
        const keyName = getKeyName(llm.provider)
        setLLM({
            ...llm,
            api_key: val,
            keys: {
                ...llm.keys,
                [keyName]: val === '' ? null : val
            }
        })
    }

    // Handle STT Key Change
    const handleSTTKeyChange = (val: string) => {
        const keyName = getKeyName(stt.provider)
        setSTT({
            ...stt,
            api_key: val,
            keys: {
                ...stt.keys,
                [keyName]: val === '' ? null : val
            }
        })
    }

    const saveLLMMutation = useMutation({
        mutationFn: (data: any) => userApi.updateConfig(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-config'] })
            toast.success('✅ LLM 配置保存成功！')
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || '保存失败')
        }
    })

    const saveSTTMutation = useMutation({
        mutationFn: (data: any) => userApi.updateConfig(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-config'] })
            toast.success('✅ STT 配置保存成功！')
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || '保存失败')
        }
    })

    const saveTTSMutation = useMutation({
        mutationFn: (data: any) => userApi.updateConfig(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-config'] })
            toast.success('✅ TTS 配置保存成功！')
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || '保存失败')
        }
    })

    const saveAllMutation = useMutation({
        mutationFn: (data: any) => userApi.updateConfig(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-config'] })
            toast.success('✅ 所有配置保存成功！')
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || '保存失败')
        }
    })

    const testLLM = useMutation({
        mutationFn: () => configApi.testLLM({
            provider: llm.provider,
            api_key: llm.api_key,
            base_url: llm.base_url,
            model: llm.model,
        }),
        onSuccess: (res) => {
            const latency = res.data.latency_ms
            setLlmTestResult({ status: 'success', message: 'AI连接测试成功', latency })
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.detail || '连接失败，请检查配置'
            setLlmTestResult({ status: 'error', message: msg })
        }
    })

    const testSTT = useMutation({
        mutationFn: () => configApi.testSTT({
            provider: stt.provider,
            api_key: stt.api_key,
            base_url: stt.base_url,
            model: stt.model,
        }),
        onSuccess: (res) => {
            const latency = res.data.latency_ms
            setSttTestResult({ status: 'success', message: 'AI连接测试成功', latency })
        },
        onError: (error: any) => {
            const msg = error?.response?.data?.detail || '连接失败，请检查配置'
            setSttTestResult({ status: 'error', message: msg })
        }
    })

    const testTTS = useMutation({
        mutationFn: () => configApi.testTTS({
            provider: tts.provider,
        }),
        onSuccess: (res) => {
            const latency = res.data.latency_ms
            setTtsTestResult({ status: 'success', message: 'TTS服务可用', latency })
        },
        onError: (error: any) => {
            const detail = error?.response?.data?.detail
            const msg = typeof detail === 'string' ? detail : '测试失败，请检查配置'
            setTtsTestResult({ status: 'error', message: msg })
        }
    })

    // Sync config to state when loaded
    useEffect(() => {
        if (config) {
            // LLM: Derive base_url and model from provider to avoid stale values
            const llmProvider = config.llm?.provider || 'GROQ'
            const llmConfig = LLM_PROVIDERS[llmProvider as keyof typeof LLM_PROVIDERS]
            // Validate model belongs to current provider, otherwise use default
            const savedLlmModel = config.llm?.model
            const isLlmModelValid = llmConfig?.models.some(m => m.id === savedLlmModel)
            setLLM({
                provider: llmProvider,
                api_key: config.llm?.api_key || '',
                base_url: llmConfig?.base_url || config.llm?.base_url || 'https://api.groq.com/openai/v1',
                model: isLlmModelValid ? savedLlmModel! : (llmConfig?.models[0]?.id || 'llama-3.3-70b-versatile'),
                keys: config.llm?.keys || {}
            })

            // STT: Derive base_url and model from provider to avoid stale values
            const sttProvider = config.stt?.provider || 'GROQ'
            const sttConfig = STT_PROVIDERS[sttProvider as keyof typeof STT_PROVIDERS]
            // Validate model belongs to current provider, otherwise use default
            const savedSttModel = config.stt?.model
            const isSttModelValid = sttConfig?.models.some(m => m.id === savedSttModel)
            setSTT({
                provider: sttProvider,
                api_key: config.stt?.api_key || '',
                base_url: sttConfig?.base_url || config.stt?.base_url || 'https://api.groq.com/openai/v1',
                model: isSttModelValid ? savedSttModel! : (sttConfig?.models[0]?.id || 'whisper-large-v3-turbo'),
                keys: config.stt?.keys || {}
            })

            setTTS({
                provider: config.tts?.provider || 'edge',
                voice: config.tts?.voice || 'zh-CN-XiaoxiaoNeural',
            })
        }
    }, [config])

    if (isLoading) {
        return <div className="card p-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
    }

    const currentLLMProvider = LLM_PROVIDERS[llm.provider as keyof typeof LLM_PROVIDERS]
    const currentSTTProvider = STT_PROVIDERS[stt.provider as keyof typeof STT_PROVIDERS]

    return (
        <div className="space-y-6">
            <toast.ToastContainer />

            {/* Tab Navigation */}
            {/* Tab Navigation */}
            <div className="flex gap-1 mb-6 border-b border-gray-200 dark:border-gray-700 overflow-x-auto pb-px">
                <button
                    onClick={() => setActiveTab('connection')}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${activeTab === 'connection'
                        ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                        }`}
                >
                    <Wallet className="w-4 h-4" />
                    AI连接配置
                </button>
                <button
                    onClick={() => setActiveTab('prompts')}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${activeTab === 'prompts'
                        ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                        }`}
                >
                    <MessageSquareCode className="w-4 h-4" />
                    提示词设置
                </button>
            </div>

            {activeTab === 'connection' ? (
                <>
                    {/* LLM */}
                    <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm">
                        <h2 className="text-lg font-semibold mb-4 text-brand-700 dark:text-brand-300">🤖 LLM 配置 (翻译/AI总结/词典)</h2>
                        <div className="grid gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Provider</label>
                                <select
                                    value={llm.provider}
                                    onChange={(e) => handleLLMProviderChange(e.target.value)}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                >
                                    <option value="SiliconFlow">SiliconFlow (硅基流动)</option>
                                    <option value="GROQ">GROQ (免费)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">API Key</label>
                                <div className="relative">
                                    <input
                                        type={showLLMKey ? 'text' : 'password'}
                                        placeholder="sk-..."
                                        value={llm.api_key}
                                        onChange={(e) => handleLLMKeyChange(e.target.value)}
                                        className="input pr-10 border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowLLMKey(!showLLMKey)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        {showLLMKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                    </button>
                                </div>
                                {llm.api_key === '***' && (
                                    <p className="text-xs text-green-600 mt-1">✓ 已设置（输入新值可覆盖）</p>
                                )}
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Base URL</label>
                                <input
                                    type="text"
                                    value={llm.base_url}
                                    onChange={(e) => setLLM({ ...llm, base_url: e.target.value })}
                                    placeholder={LLM_PROVIDERS[llm.provider as keyof typeof LLM_PROVIDERS]?.base_url}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Model</label>
                                <select
                                    value={llm.model}
                                    onChange={(e) => setLLM({ ...llm, model: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                >
                                    {currentLLMProvider?.models.map((m) => (
                                        <option key={m.id} value={m.id}>
                                            {m.name} - {m.pricing}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Balance Card */}
                            <BalanceCard serviceType="llm" provider={llm.provider} />

                            <div className="mt-4">
                                <TestResultDisplay
                                    result={llmTestResult}
                                    onClear={() => setLlmTestResult({ status: null, message: '' })}
                                />
                                <div className="flex items-center justify-center gap-3">
                                    <button
                                        onClick={() => testLLM.mutate()}
                                        disabled={testLLM.isPending || !llm.api_key}
                                        className="btn-secondary flex items-center gap-2 border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                                    >
                                        {testLLM.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Zap className="w-4 h-4" />
                                        )}
                                        测试 AI 连接
                                    </button>
                                    <button
                                        onClick={() => saveLLMMutation.mutate({ llm })}
                                        disabled={saveLLMMutation.isPending}
                                        className="btn-primary flex items-center gap-2"
                                    >
                                        {saveLLMMutation.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Save className="w-4 h-4" />
                                        )}
                                        保存配置
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* STT */}
                    <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm">
                        <h2 className="text-lg font-semibold mb-4 text-brand-700 dark:text-brand-300">🎤 STT 配置 (语音转文字)</h2>
                        <div className="grid gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Provider</label>
                                <select
                                    value={stt.provider}
                                    onChange={(e) => handleSTTProviderChange(e.target.value)}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                >
                                    <option value="SiliconFlow">SiliconFlow (硅基流动)</option>
                                    <option value="GROQ">GROQ (免费)</option>
                                    <option value="OpenAI">OpenAI (付费)</option>
                                    <option value="Deepgram">Deepgram (付费)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">API Key</label>
                                <div className="relative">
                                    <input
                                        type={showSTTKey ? 'text' : 'password'}
                                        placeholder={stt.provider === 'GROQ' ? 'gsk_...' : 'sk-...'}
                                        value={stt.api_key}
                                        onChange={(e) => handleSTTKeyChange(e.target.value)}
                                        className="input pr-10 border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowSTTKey(!showSTTKey)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        {showSTTKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                    </button>
                                </div>
                                {stt.api_key === '***' && (
                                    <p className="text-xs text-green-600 mt-1">✓ 已设置（输入新值可覆盖）</p>
                                )}
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Base URL</label>
                                <input
                                    type="text"
                                    value={stt.base_url}
                                    onChange={(e) => setSTT({ ...stt, base_url: e.target.value })}
                                    placeholder={STT_PROVIDERS[stt.provider as keyof typeof STT_PROVIDERS]?.base_url}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Model</label>
                                <select
                                    value={stt.model}
                                    onChange={(e) => setSTT({ ...stt, model: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                >
                                    {currentSTTProvider?.models.map((m) => (
                                        <option key={m.id} value={m.id}>
                                            {m.name} - {m.accuracy} - {m.pricing}
                                        </option>
                                    ))}
                                </select>
                                {stt.provider === 'GROQ' && (
                                    <p className="text-xs text-gray-500 mt-1">
                                        💡 推荐使用 whisper-large-v3-turbo，免费且准确率极高
                                    </p>
                                )}
                            </div>

                            {/* Balance Card */}
                            <BalanceCard serviceType="stt" provider={stt.provider} />

                            <div className="mt-4">
                                <TestResultDisplay
                                    result={sttTestResult}
                                    onClear={() => setSttTestResult({ status: null, message: '' })}
                                />
                                <div className="flex items-center justify-center gap-3">
                                    <button
                                        onClick={() => testSTT.mutate()}
                                        disabled={testSTT.isPending || !stt.api_key}
                                        className="btn-secondary flex items-center gap-2 border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                                    >
                                        {testSTT.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Zap className="w-4 h-4" />
                                        )}
                                        测试 AI 连接
                                    </button>
                                    <button
                                        onClick={() => saveSTTMutation.mutate({ stt })}
                                        disabled={saveSTTMutation.isPending}
                                        className="btn-primary flex items-center gap-2"
                                    >
                                        {saveSTTMutation.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Save className="w-4 h-4" />
                                        )}
                                        保存配置
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* TTS */}
                    <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm">
                        <h2 className="text-lg font-semibold mb-4 text-brand-700 dark:text-brand-300">🔊 TTS 配置 (文字转语音)</h2>
                        <div className="grid gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Provider</label>
                                <select
                                    value={tts.provider}
                                    onChange={(e) => setTTS({ ...tts, provider: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                >
                                    <option value="edge">Edge TTS (免费)</option>
                                    <option value="openai">OpenAI TTS</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Voice</label>
                                <select
                                    value={tts.voice}
                                    onChange={(e) => setTTS({ ...tts, voice: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                >
                                    <option value="zh-CN-XiaoxiaoNeural">晓晓 (女)</option>
                                    <option value="zh-CN-YunxiNeural">云希 (男)</option>
                                    <option value="en-US-JennyNeural">Jenny (Female)</option>
                                    <option value="en-US-GuyNeural">Guy (Male)</option>
                                </select>
                            </div>
                            <div className="mt-2">
                                <TestResultDisplay
                                    result={ttsTestResult}
                                    onClear={() => setTtsTestResult({ status: null, message: '' })}
                                />
                                <div className="flex items-center justify-center gap-3">
                                    <button
                                        onClick={() => testTTS.mutate()}
                                        disabled={testTTS.isPending}
                                        className="btn-secondary flex items-center gap-2 border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                                    >
                                        {testTTS.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Zap className="w-4 h-4" />
                                        )}
                                        测试 TTS
                                    </button>
                                    <button
                                        onClick={() => saveTTSMutation.mutate({ tts })}
                                        disabled={saveTTSMutation.isPending}
                                        className="btn-primary flex items-center gap-2"
                                    >
                                        {saveTTSMutation.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Save className="w-4 h-4" />
                                        )}
                                        保存配置
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Save */}
                    <div className="flex justify-center">
                        <button
                            onClick={() => saveAllMutation.mutate({ llm, stt, tts })}
                            disabled={saveAllMutation.isPending}
                            className="btn-primary"
                        >
                            {saveAllMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                            保存所有配置
                        </button>
                    </div>
                </>
            ) : (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                    <AIPromptsSettings />
                </div>
            )}
        </div>
    )
}
