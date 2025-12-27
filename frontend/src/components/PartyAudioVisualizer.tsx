/**
 * PartyAudioVisualizer Component (v3 - 炫酷版)
 * 派对音量可视化 - 超灵敏、超炫酷
 * 
 * 5个阶段 (极低阈值，超灵敏):
 * 1. 静音 (0-2%): 1人睡觉
 * 2. 微弱 (2-10%): 1人摇摆
 * 3. 正常 (10-25%): 2人摇摆
 * 4. 较大 (25-50%): 3人跳舞
 * 5. 爆发 (50-100%): 狂欢派对
 */
import { useMemo } from 'react'

interface PartyAudioVisualizerProps {
    volume: number // 0-100
}

type VisualizerState = 'sleeping' | 'waking' | 'grooving' | 'dancing' | 'party'

// 单个小人 SVG
function Stickman({
    pose,
    color = '#6366f1',
    glow = false,
    style = {},
}: {
    pose: 'sleep' | 'stand' | 'wave' | 'jump'
    color?: string
    glow?: boolean
    style?: React.CSSProperties
}) {
    const glowFilter = glow ? `drop-shadow(0 0 6px ${color})` : 'none'

    return (
        <svg
            viewBox="0 0 40 60"
            className="w-6 h-9"
            style={{ ...style, filter: glowFilter }}
        >
            {pose === 'sleep' ? (
                <>
                    <circle cx="20" cy="18" r="8" fill={color} />
                    <line x1="20" y1="26" x2="20" y2="42" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="30" x2="10" y2="38" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="30" x2="30" y2="38" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="42" x2="12" y2="55" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="42" x2="28" y2="55" stroke={color} strokeWidth="3" strokeLinecap="round" />
                </>
            ) : pose === 'stand' ? (
                <>
                    <circle cx="20" cy="12" r="8" fill={color} />
                    <line x1="20" y1="20" x2="20" y2="38" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="26" x2="8" y2="32" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="26" x2="32" y2="32" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="38" x2="12" y2="55" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="38" x2="28" y2="55" stroke={color} strokeWidth="3" strokeLinecap="round" />
                </>
            ) : pose === 'wave' ? (
                <>
                    <circle cx="20" cy="10" r="8" fill={color} />
                    <line x1="20" y1="18" x2="20" y2="36" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="24" x2="8" y2="18" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="24" x2="32" y2="30" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="36" x2="12" y2="52" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="36" x2="28" y2="52" stroke={color} strokeWidth="3" strokeLinecap="round" />
                </>
            ) : (
                <>
                    <circle cx="20" cy="8" r="8" fill={color} />
                    <line x1="20" y1="16" x2="20" y2="34" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="22" x2="6" y2="12" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="22" x2="34" y2="12" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="34" x2="10" y2="50" stroke={color} strokeWidth="3" strokeLinecap="round" />
                    <line x1="20" y1="34" x2="30" y2="50" stroke={color} strokeWidth="3" strokeLinecap="round" />
                </>
            )}
        </svg>
    )
}

// 漂浮的音符/星星粒子
function FloatingParticle({ emoji, delay, duration }: { emoji: string; delay: number; duration: number }) {
    return (
        <span
            className="absolute text-sm"
            style={{
                animation: `floatUp ${duration}s ease-out infinite`,
                animationDelay: `${delay}s`,
                left: `${Math.random() * 80 + 10}%`,
                bottom: 0,
            }}
        >
            {emoji}
        </span>
    )
}

export function PartyAudioVisualizer({ volume }: PartyAudioVisualizerProps) {
    // 超灵敏阈值
    const state: VisualizerState = useMemo(() => {
        if (volume < 2) return 'sleeping'
        if (volume < 10) return 'waking'
        if (volume < 25) return 'grooving'
        if (volume < 50) return 'dancing'
        return 'party'
    }, [volume])

    // 动态缩放：音量越大，整体越大
    const scale = 1 + (volume / 200)

    // 动画速度
    const animDuration = Math.max(0.6, 1.2 - (volume / 120))

    // 颜色  
    const colors = {
        sleep: '#9ca3af',
        primary: '#6366f1',
        secondary: '#8b5cf6',
        tertiary: '#a78bfa',
        neon: ['#ff00ff', '#00ffff', '#ffff00', '#ff6600', '#00ff00']
    }

    return (
        <div
            className="flex items-center justify-center h-14 min-w-[140px] px-2 relative"
            style={{ transform: `scale(${scale})`, transition: 'transform 0.15s ease-out' }}
        >
            {/* 全局动画样式 */}
            <style>{`
                @keyframes sway {
                    0%, 100% { transform: translateY(0px) rotate(0deg); }
                    25% { transform: translateY(-4px) rotate(-5deg); }
                    75% { transform: translateY(-4px) rotate(5deg); }
                }
                @keyframes jump {
                    0%, 100% { transform: translateY(0px) scaleY(1); }
                    50% { transform: translateY(-8px) scaleY(1.1); }
                }
                @keyframes floatUp {
                    0% { transform: translateY(0) scale(1); opacity: 1; }
                    100% { transform: translateY(-30px) scale(0.5); opacity: 0; }
                }
                @keyframes disco {
                    0% { filter: hue-rotate(0deg) drop-shadow(0 0 8px currentColor); }
                    100% { filter: hue-rotate(360deg) drop-shadow(0 0 12px currentColor); }
                }
                @keyframes pulse-bg {
                    0%, 100% { opacity: 0.3; transform: scale(1); }
                    50% { opacity: 0.6; transform: scale(1.1); }
                }
            `}</style>

            {/* 状态 1: 睡觉 */}
            {state === 'sleeping' && (
                <div
                    className="flex items-center gap-1"
                    style={{ opacity: 0.5, animation: 'sway 3s ease-in-out infinite' }}
                >
                    <Stickman pose="sleep" color={colors.sleep} />
                    <span className="text-gray-400 text-xs">z Z z</span>
                </div>
            )}

            {/* 状态 2: 醒来 - 开始摇摆 */}
            {state === 'waking' && (
                <div style={{ animation: `sway ${animDuration + 0.3}s ease-in-out infinite` }}>
                    <Stickman pose="stand" color={colors.primary} glow />
                </div>
            )}

            {/* 状态 3: 2人摇摆 */}
            {state === 'grooving' && (
                <div className="flex items-end gap-1 relative">
                    <div style={{ animation: `sway ${animDuration}s ease-in-out infinite` }}>
                        <Stickman pose="wave" color={colors.primary} glow />
                    </div>
                    <div style={{ animation: `sway ${animDuration}s ease-in-out infinite`, animationDelay: '0.2s' }}>
                        <Stickman pose="wave" color={colors.secondary} glow />
                    </div>
                    <span className="text-lg ml-1" style={{ animation: 'sway 0.8s ease-in-out infinite' }}>🎵</span>
                </div>
            )}

            {/* 状态 4: 3人跳舞 */}
            {state === 'dancing' && (
                <div className="flex items-end gap-0.5 relative">
                    {[colors.primary, colors.secondary, colors.tertiary].map((c, i) => (
                        <div
                            key={i}
                            style={{
                                animation: `jump ${animDuration}s ease-in-out infinite`,
                                animationDelay: `${i * 0.12}s`
                            }}
                        >
                            <Stickman pose="jump" color={c} glow />
                        </div>
                    ))}
                    <div className="ml-1 relative h-8 w-6">
                        <span className="absolute" style={{ animation: 'floatUp 1.2s ease-out infinite' }}>🎵</span>
                        <span className="absolute" style={{ animation: 'floatUp 1.4s ease-out infinite', animationDelay: '0.5s' }}>✨</span>
                    </div>
                </div>
            )}

            {/* 状态 5: 狂欢派对！！ */}
            {state === 'party' && (
                <div className="relative flex items-center">
                    {/* 迪斯科背景光效 */}
                    <div
                        className="absolute -inset-2 rounded-2xl"
                        style={{
                            background: 'linear-gradient(45deg, #ff00ff33, #00ffff33, #ffff0033, #ff660033)',
                            animation: 'pulse-bg 0.5s ease-in-out infinite',
                        }}
                    />

                    {/* 霓虹小人群 */}
                    <div
                        className="flex items-end gap-0 relative z-10"
                        style={{ animation: `disco ${animDuration}s linear infinite` }}
                    >
                        {colors.neon.map((c, i) => (
                            <div
                                key={i}
                                style={{
                                    animation: `jump ${animDuration - 0.1}s ease-in-out infinite`,
                                    animationDelay: `${i * 0.08}s`
                                }}
                            >
                                <Stickman pose="jump" color={c} glow />
                            </div>
                        ))}
                    </div>

                    {/* 漂浮粒子 */}
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                        {['✨', '🎵', '⭐', '🎶', '💫'].map((e, i) => (
                            <FloatingParticle key={i} emoji={e} delay={i * 0.3} duration={1.5} />
                        ))}
                    </div>

                    {/* PARTY 文字 */}
                    <div
                        className="ml-2 text-xs font-bold relative z-10"
                        style={{
                            background: 'linear-gradient(90deg, #ff00ff, #00ffff, #ffff00)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            animation: 'disco 0.5s linear infinite'
                        }}
                    >
                        PARTY!
                    </div>
                </div>
            )}
        </div>
    )
}
