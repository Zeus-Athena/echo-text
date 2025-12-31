
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userApi } from '@/api/client'
import { useToast } from '@/components/Toast'
import { useNoiseDetection } from '@/hooks/useNoiseDetection'
import { Save, Loader2, Mic, Settings2, Sparkles, Zap, Layers, ShieldAlert, Activity } from 'lucide-react'
import clsx from 'clsx'
import { useAppStore } from '@/stores/app'

/**
 * Recording Settings Page
 * 
 * DESIGN: Independent Cards Layout (No outer wrapper)
 * Consistent with APISettings.tsx
 */
export function RecordingSettings() {
    const queryClient = useQueryClient()
    const toast = useToast()
    const { detectNoise, isDetecting } = useNoiseDetection()
    const { accentColor } = useAppStore()

    const { data: config } = useQuery({
        queryKey: ['user-config'],
        queryFn: () => userApi.getConfig(),
        select: (res) => res.data,
    })

    const [bufferDuration, setBufferDuration] = useState(6)
    const [silenceThreshold, setSilenceThreshold] = useState(30)
    const [silencePreferSource, setSilencePreferSource] = useState<'current' | 'auto'>('current')
    const [thresholdSource, setThresholdSource] = useState<'default' | 'manual' | 'manual_detect' | 'auto'>('default')
    const [translationMode, setTranslationMode] = useState(100)  // RPM 限制，默认 100
    const [translationBurst, setTranslationBurst] = useState(10)  // 令牌桶容量，默认 10
    const [softThreshold, setSoftThreshold] = useState(50)
    const [hardThreshold, setHardThreshold] = useState(100)

    // 使用后端返回的 is_true_streaming 判断显示哪个配置项
    const isTrueStreaming = config?.stt?.is_true_streaming ?? false

    useEffect(() => {
        if (config?.recording) {
            setBufferDuration(config.recording.audio_buffer_duration ?? 6)
            setSilenceThreshold(config.recording.silence_threshold ?? 30)
            const preferSource = config.recording.silence_prefer_source
            setSilencePreferSource(preferSource === 'manual' ? 'current' : (preferSource as 'current' | 'auto') ?? 'current')
            setThresholdSource((config.recording.silence_threshold_source as any) ?? 'default')
            // RPM 配置：老数据 (0, 6) 自动修正为 100
            const rawRpm = config.recording.translation_mode ?? 100
            setTranslationMode(rawRpm)
            // Burst 配置：老数据无字段默认 10
            const rawBurst = config.recording.translation_burst ?? 10
            setTranslationBurst(rawBurst)
            setSoftThreshold(config.recording.segment_soft_threshold ?? 50)
            setHardThreshold(config.recording.segment_hard_threshold ?? 100)
        }
    }, [config])

    const saveMutation = useMutation({
        mutationFn: (data: any) => userApi.updateConfig({
            recording: {
                audio_buffer_duration: data.bufferDuration,
                silence_threshold: data.silenceThreshold,
                silence_prefer_source: data.silencePreferSource,
                silence_threshold_source: data.thresholdSource,
                translation_mode: data.translationMode,
                translation_burst: data.translationBurst,
                segment_soft_threshold: data.softThreshold,
                segment_hard_threshold: data.hardThreshold
            }
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-config'] })
            toast.success('✅ 配置已保存')
        },
        onError: (err: any) => {
            toast.error(err?.response?.data?.detail || '保存失败')
        }
    })

    const handleSave = () => {
        saveMutation.mutate({
            bufferDuration,
            silenceThreshold,
            silencePreferSource,
            thresholdSource,
            translationMode,
            translationBurst,
            softThreshold,
            hardThreshold
        })
    }

    const markers = [
        { value: 0, label: '录音棚' },
        { value: 20, label: '安静' },
        { value: 40, label: '办公室' },
        { value: 60, label: '嘈杂' },
        { value: 80, label: '工厂' },
    ]

    const handleSliderChange = (value: number) => {
        setSilenceThreshold(value)
        setThresholdSource('manual')
    }

    const handleDetectNoise = async () => {
        try {
            const detected = await detectNoise()
            setSilenceThreshold(detected)
            setThresholdSource('manual_detect')
            toast.success(`✅ 检测完成，推荐阈值: ${detected}`)
        } catch (err) {
            toast.error('环境检测失败，请确保麦克风权限已开启')
        }
    }

    return (
        <div className="space-y-6">
            <toast.ToastContainer />

            {/* CARD 1: Transcription Strategy */}
            <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm bg-white dark:bg-slate-900 rounded-xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
                        <Zap className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg text-brand-700 dark:text-brand-300 leading-tight">转录处理策略</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">控制音频流的处理方式与响应速度</p>
                    </div>
                </div>

                {!isTrueStreaming ? (
                    <div className="space-y-6">
                        <div className="space-y-3">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                音频缓冲时长
                            </label>
                            <div className="relative">
                                <select
                                    value={bufferDuration}
                                    onChange={(e) => setBufferDuration(Number(e.target.value))}
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-800 dark:text-slate-200 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 appearance-none transition-all cursor-pointer"
                                >
                                    <option value={3}>3 秒 (极速响应)</option>
                                    <option value={4}>4 秒 (推荐体验)</option>
                                    <option value={6}>6 秒 (完整语义)</option>
                                    <option value={10}>10 秒 (会议优先)</option>
                                </select>
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                                    ▼
                                </div>
                            </div>
                        </div>
                        <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800">
                            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                                决定积累多长音频后发送给 AI。<b>短时间</b>适合快速对话；<b>长时间</b>能获得更准确的上下文理解。
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* RPM 限制滑块 */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    翻译速率限制 (RPM)
                                </label>
                                <div className="bg-brand-50 dark:bg-brand-900/10 px-3 py-1 rounded-full border border-brand-100 dark:border-brand-900/20">
                                    <span className="font-mono text-brand-600 dark:text-brand-400 font-bold text-xs">
                                        {translationMode} 次/分钟
                                    </span>
                                </div>
                            </div>
                            <div className="relative h-10 w-full flex items-center">
                                <div className="absolute left-0 right-0 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full" />
                                <div
                                    className="absolute left-0 h-1.5 bg-brand-500 rounded-full"
                                    style={{ width: `${(translationMode - 1) / (300 - 1) * 100}%` }}
                                />
                                <input
                                    type="range" min="1" max="300" step="1"
                                    value={translationMode}
                                    onChange={(e) => setTranslationMode(Number(e.target.value))}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                />
                                <div
                                    className="absolute w-5 h-5 bg-white dark:bg-brand-50 rounded-full border-2 border-brand-500 shadow-sm pointer-events-none transition-transform z-10"
                                    style={{ left: `calc(${(translationMode - 1) / (300 - 1) * 100}% - 10px)` }}
                                />
                            </div>
                            <p className="text-xs text-gray-500">
                                每分钟最大翻译请求次数。较高值响应更快，但可能触发 LLM API 限流。推荐：Groq 免费版设 60，付费 API 设 100-200
                            </p>
                        </div>

                        {/* 桶容量 (Burst) 滑块 */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    桶容量 (Burst)
                                </label>
                                <div className="bg-brand-50 dark:bg-brand-900/10 px-3 py-1 rounded-full border border-brand-100 dark:border-brand-900/20">
                                    <span className="font-mono text-brand-600 dark:text-brand-400 font-bold text-xs">
                                        {translationBurst} 次
                                    </span>
                                </div>
                            </div>
                            <div className="relative h-10 w-full flex items-center">
                                <div className="absolute left-0 right-0 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full" />
                                <div
                                    className="absolute left-0 h-1.5 bg-brand-500 rounded-full"
                                    style={{ width: `${(translationBurst - 1) / (100 - 1) * 100}%` }}
                                />
                                <input
                                    type="range" min="1" max="100" step="1"
                                    value={translationBurst}
                                    onChange={(e) => setTranslationBurst(Number(e.target.value))}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                />
                                <div
                                    className="absolute w-5 h-5 bg-white dark:bg-brand-50 rounded-full border-2 border-brand-500 shadow-sm pointer-events-none transition-transform z-10"
                                    style={{ left: `calc(${(translationBurst - 1) / (100 - 1) * 100}% - 10px)` }}
                                />
                            </div>
                            <p className="text-xs text-gray-500">
                                允许短时间内超过 RPM 限制的最大请求数。应对对话密集场景，推荐 10-30
                            </p>
                        </div>

                        <div className="p-4 bg-brand-50 dark:bg-brand-900/10 rounded-xl border border-brand-100 dark:border-brand-900/20 flex items-start gap-3">
                            <Activity className="w-4 h-4 text-brand-500 mt-0.5" />
                            <p className="text-xs text-brand-700 dark:text-brand-300 leading-relaxed">
                                当前使用实时流式转录。系统将按完整句子触发翻译，并根据 RPM 限制控制请求频率。
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* CARD 2: VAD */}
            <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm bg-white dark:bg-slate-900 rounded-xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
                        <Settings2 className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg text-brand-700 dark:text-brand-300 leading-tight">环境适应 (VAD)</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">智能调节麦克风对环境噪音的敏感度</p>
                    </div>
                </div>

                <div className="space-y-8">
                    <div className="flex justify-between items-end">
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">静音检测阈值</p>
                            <h4 className="text-2xl font-bold text-brand-600 dark:text-brand-400 font-mono tracking-tighter">{silenceThreshold}%</h4>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleDetectNoise}
                                disabled={isDetecting}
                                className="p-2 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-brand-600 dark:text-brand-400 transition-colors disabled:opacity-50 border border-slate-200 dark:border-slate-700"
                                title="检测当前环境"
                            >
                                {isDetecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>

                    <div className="relative h-14 w-full flex items-center">
                        {/* Track */}
                        <div className="absolute left-0 right-0 h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                        </div>
                        <div
                            className="absolute left-0 h-2 bg-brand-500 dark:bg-brand-500 rounded-full"
                            style={{ width: `${silenceThreshold}%` }}
                        />

                        {/* Input - Full Cover */}
                        <input
                            type="range"
                            min="0" max="100" step="1"
                            value={silenceThreshold}
                            onChange={(e) => handleSliderChange(Number(e.target.value))}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                        />

                        {/* Custom Thumb - Standard */}
                        <div
                            className="absolute w-6 h-6 bg-white dark:bg-slate-100 border-2 border-brand-500 dark:border-brand-400 rounded-full shadow-md pointer-events-none transition-transform z-10 flex items-center justify-center"
                            style={{ left: `calc(${silenceThreshold}% - 12px)` }}
                        >
                        </div>
                    </div>

                    <div className="flex justify-between px-1">
                        {markers.map((m, idx) => (
                            <div key={idx} className="flex flex-col items-center gap-2 group">
                                <div className="w-8 h-8 rounded-lg bg-slate-50 dark:bg-slate-800 flex items-center justify-center border border-slate-200 dark:border-slate-700 group-hover:bg-slate-100 dark:group-hover:bg-slate-700 transition-colors">
                                    <div className={clsx("w-1 h-3 rounded-full transition-colors", silenceThreshold > m.value ? "bg-brand-400" : "bg-slate-300 dark:bg-slate-600")} />
                                </div>
                                <span className="text-[10px] font-medium text-gray-500 tracking-wider">{m.label}</span>
                            </div>
                        ))}
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-800">
                        <span className="text-xs text-gray-500">检测模式</span>
                        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                            {(['current', 'auto'] as const).map(mode => (
                                <button
                                    key={mode}
                                    onClick={() => setSilencePreferSource(mode)}
                                    className={clsx(
                                        "px-3 py-1 rounded-md text-[10px] font-bold uppercase transition-all",
                                        silencePreferSource === mode
                                            ? "bg-white dark:bg-slate-700 text-brand-600 dark:text-brand-300 shadow-sm"
                                            : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-400"
                                    )}
                                >
                                    {mode === 'current' ? '手动' : '自动'}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* CARD 3: Segmentation */}
            <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm bg-white dark:bg-slate-900 rounded-xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                        <Layers className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg text-brand-700 dark:text-brand-300 leading-tight">卡片分段 (Segmentation)</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">控制生成卡片的字数与切割粒度</p>
                    </div>
                </div>

                <div className="space-y-8">
                    {/* Soft Threshold */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">软阈值 (首选字数)</label>
                            <div className="bg-emerald-50 dark:bg-emerald-900/10 px-3 py-1 rounded-full border border-emerald-100 dark:border-emerald-900/20">
                                <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold text-xs">{softThreshold} 词</span>
                            </div>
                        </div>
                        <div className="relative h-10 w-full flex items-center">
                            <div className="absolute left-0 right-0 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full" />
                            <div
                                className="absolute left-0 h-1.5 bg-emerald-500 rounded-full"
                                style={{ width: `${(softThreshold - 10) / (200 - 10) * 100}%` }}
                            />
                            <input
                                type="range" min="10" max="200" step="5"
                                value={softThreshold}
                                onChange={(e) => setSoftThreshold(Number(e.target.value))}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                            />
                            <div
                                className="absolute w-5 h-5 bg-white dark:bg-emerald-50 rounded-full border-2 border-emerald-500 shadow-sm pointer-events-none transition-transform z-10"
                                style={{ left: `calc(${(softThreshold - 10) / (200 - 10) * 100}% - 10px)` }}
                            />
                        </div>
                        <p className="text-xs text-gray-500">
                            理想单卡片字数。系统会在该字数附近寻找标点符号进行自然断句。
                        </p>
                    </div>

                    {/* Hard Threshold */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">硬上限 (最大字数)</label>
                            <div className="bg-rose-50 dark:bg-rose-900/10 px-3 py-1 rounded-full border border-rose-100 dark:border-rose-900/20">
                                <span className="font-mono text-rose-600 dark:text-rose-400 font-bold text-xs">{hardThreshold} 词</span>
                            </div>
                        </div>
                        <div className="relative h-10 w-full flex items-center">
                            <div className="absolute left-0 right-0 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full" />
                            <div
                                className="absolute left-0 h-1.5 bg-rose-500 rounded-full"
                                style={{ width: `${(hardThreshold - 30) / (500 - 30) * 100}%` }}
                            />
                            <input
                                type="range" min="30" max="500" step="10"
                                value={hardThreshold}
                                onChange={(e) => setHardThreshold(Number(e.target.value))}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                            />
                            <div
                                className="absolute w-5 h-5 bg-white dark:bg-rose-50 rounded-full border-2 border-rose-500 shadow-sm pointer-events-none transition-transform z-10"
                                style={{ left: `calc(${(hardThreshold - 30) / (500 - 30) * 100}% - 10px)` }}
                            />
                        </div>
                        <p className="text-xs text-gray-500">
                            强制分段字数。即使找不到标点，超过此限制也会强制切分，防止卡片过长。
                        </p>
                    </div>

                    {/* Visualizer - Minimalist */}
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-100 dark:border-slate-800 flex flex-col items-center gap-2">
                        <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden flex">
                            <div className="h-full bg-slate-400 dark:bg-slate-500" style={{ width: '30%' }} />
                            <div className="h-full bg-transparent w-[2px]" />
                            <div className="h-full bg-slate-400 dark:bg-slate-500" style={{ width: '40%' }} />
                        </div>
                        <span className="text-xs text-gray-500 font-mono">
                            约 {softThreshold} ~ {hardThreshold} 字 / 卡片
                        </span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-4 p-4 bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/20 rounded-2xl">
                <ShieldAlert className="w-5 h-5 text-amber-500" />
                <p className="text-xs text-amber-700 dark:text-amber-400 font-medium">
                    分段设置会实时影响后续的转录卡片生成。建议调整后进行简短录音测试。
                </p>
            </div>

            {/* SUBMIT BUTTON - Clean Pill */}
            <div className="flex justify-center pt-8 pb-12">
                <button
                    onClick={handleSave}
                    disabled={saveMutation.isPending}
                    className="group relative px-8 h-12 bg-brand-600 text-white rounded-full shadow-lg hover:shadow-xl hover:bg-brand-700 transition-all font-bold tracking-wide disabled:opacity-50 disabled:hover:scale-100 active:scale-95 flex items-center gap-2"
                >
                    {saveMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                    保存所有配置
                </button>
            </div>
        </div>
    )
}
