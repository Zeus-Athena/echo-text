/**
 * AudioPlayerSection Component
 * 音频播放器区域组件
 */
import { memo } from 'react'
import {
    Play,
    Pause,
    Volume2,
    VolumeX,
    SkipBack,
    SkipForward,
    Loader2,
} from 'lucide-react'
import PlaybackWaveform from './PlaybackWaveform'

interface AudioPlayerSectionProps {
    // Audio state
    isPlaying: boolean
    currentTime: number
    duration: number
    volume: number
    playbackSpeed: number
    audioBlobUrl: string | null
    audioError: string | null
    isLoading: boolean
    recordingDuration: number

    // Callbacks
    onTogglePlay: () => void
    onVolumeChange: (volume: number) => void
    onSpeedChange: (speed: number) => void
    onSkipTime: (seconds: number) => void
    onSeek: (time: number) => void
    onDurationReady?: (duration: number) => void
    formatTime: (seconds: number) => string
}

function AudioPlayerSectionComponent({
    isPlaying,
    currentTime,
    duration,
    volume,
    playbackSpeed,
    audioBlobUrl,
    audioError,
    isLoading,
    recordingDuration,
    onTogglePlay,
    onVolumeChange,
    onSpeedChange,
    onSkipTime,
    onSeek,
    onDurationReady,
    formatTime
}: AudioPlayerSectionProps) {
    const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        onVolumeChange(parseFloat(e.target.value))
    }

    if (audioError) {
        return (
            <div className="card p-4 mb-6">
                <div className="text-center text-red-500 py-2">
                    {audioError}
                </div>
            </div>
        )
    }

    if (isLoading || !audioBlobUrl) {
        return (
            <div className="card p-4 mb-6">
                <div className="flex items-center justify-center py-2 text-gray-500">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    加载音频中...
                </div>
            </div>
        )
    }

    return (
        <div className="card p-4 mb-6">
            <div className="flex items-center gap-6">
                {/* 1. Skip Back */}
                <button
                    onClick={() => onSkipTime(-5)}
                    className="p-2 text-gray-400 hover:text-brand-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors shrink-0"
                    title="快退 5 秒"
                >
                    <SkipBack className="w-5 h-5" />
                </button>

                {/* 2. Play/Pause */}
                <button
                    onClick={onTogglePlay}
                    className="w-12 h-12 rounded-full bg-brand-500 text-white flex items-center justify-center hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/20 shrink-0"
                >
                    {isPlaying ? (
                        <Pause className="w-5 h-5 fill-current" />
                    ) : (
                        <Play className="w-5 h-5 fill-current ml-0.5" />
                    )}
                </button>

                {/* 3. Skip Forward */}
                <button
                    onClick={() => onSkipTime(5)}
                    className="p-2 text-gray-400 hover:text-brand-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors shrink-0"
                    title="快进 5 秒"
                >
                    <SkipForward className="w-5 h-5" />
                </button>

                {/* 4. Waveform (flex-grow) */}
                <div className="flex-1 flex flex-col justify-center h-14">
                    <PlaybackWaveform
                        audioUrl={audioBlobUrl}
                        currentTime={currentTime}
                        isPlaying={isPlaying}
                        volume={volume}
                        onSeek={onSeek}
                        onReady={onDurationReady}
                        height={40}
                    />
                    <div className="relative top-0 flex justify-between text-xs text-gray-400 font-mono mt-1 pointer-events-none select-none">
                        <span>{formatTime(currentTime)}</span>
                        <span>{formatTime(duration || recordingDuration)}</span>
                    </div>
                </div>

                {/* 5. Speed */}
                <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-gray-400">速度</span>
                    <select
                        value={playbackSpeed}
                        onChange={(e) => onSpeedChange(Number(e.target.value))}
                        className="bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded pl-2 pr-7 py-0.5 cursor-pointer outline-none text-xs text-gray-600 dark:text-gray-300 border border-transparent focus:border-brand-200 dark:focus:border-brand-800 h-7"
                    >
                        <option value="0.5">0.5x</option>
                        <option value="1">1.0x</option>
                        <option value="1.25">1.25x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2">2.0x</option>
                    </select>
                </div>

                {/* 6. Volume */}
                <div className="relative group shrink-0">
                    <button
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        {volume === 0 ? (
                            <VolumeX className="w-5 h-5" />
                        ) : (
                            <Volume2 className="w-5 h-5" />
                        )}
                    </button>
                    {/* Clean Horizontal Volume Slider Popup */}
                    <div className="absolute bottom-full right-0 w-40 pb-2 hidden group-hover:block hover:block">
                        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-100 dark:border-gray-700 p-3 flex items-center gap-2 h-10">
                            <div className="relative flex-1 h-4 flex items-center">
                                {/* Track background */}
                                <div className="absolute inset-x-0 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full" />
                                {/* Progress fill */}
                                <div
                                    className="absolute h-1.5 bg-brand-500 rounded-full transition-all"
                                    style={{ width: `${volume * 100}%` }}
                                />
                                {/* Slider input */}
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={volume}
                                    onChange={handleVolumeChange}
                                    className="relative w-full h-4 appearance-none bg-transparent cursor-pointer z-10
                                        [&::-webkit-slider-thumb]:appearance-none
                                        [&::-webkit-slider-thumb]:w-3.5
                                        [&::-webkit-slider-thumb]:h-3.5
                                        [&::-webkit-slider-thumb]:rounded-full
                                        [&::-webkit-slider-thumb]:bg-white
                                        [&::-webkit-slider-thumb]:border-2
                                        [&::-webkit-slider-thumb]:border-brand-500
                                        [&::-webkit-slider-thumb]:shadow-md
                                        [&::-webkit-slider-thumb]:cursor-pointer
                                        [&::-webkit-slider-thumb]:transition-transform
                                        [&::-webkit-slider-thumb]:hover:scale-110
                                        [&::-moz-range-thumb]:w-3.5
                                        [&::-moz-range-thumb]:h-3.5
                                        [&::-moz-range-thumb]:rounded-full
                                        [&::-moz-range-thumb]:bg-white
                                        [&::-moz-range-thumb]:border-2
                                        [&::-moz-range-thumb]:border-brand-500
                                        [&::-moz-range-thumb]:shadow-md
                                        [&::-moz-range-thumb]:cursor-pointer"
                                />
                            </div>
                            {/* Volume percentage */}
                            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 w-8 text-right tabular-nums">
                                {Math.round(volume * 100)}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export const AudioPlayerSection = memo(AudioPlayerSectionComponent)
