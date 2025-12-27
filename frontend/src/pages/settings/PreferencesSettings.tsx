
import { useAppStore } from '@/stores/app'
import clsx from 'clsx'

export function PreferencesSettings() {
    const { theme, setTheme, accentColor, setAccentColor } = useAppStore()

    return (
        <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm">
            <h2 className="text-lg font-semibold mb-6 text-brand-700 dark:text-brand-300">偏好设置</h2>

            <div className="space-y-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">主题</label>
                    <div className="flex gap-2">
                        {(['light', 'dark', 'system'] as const).map((t) => (
                            <button
                                key={t}
                                onClick={() => setTheme(t)}
                                className={clsx(
                                    'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                                    theme === t
                                        ? 'bg-brand-600 text-white'
                                        : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-brand-200 dark:border-brand-800'
                                )}
                            >
                                {t === 'light' ? '浅色' : t === 'dark' ? '深色' : '跟随系统'}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">主题色</label>
                    <div className="flex flex-wrap gap-3">
                        <button
                            onClick={() => setAccentColor('purple')}
                            className={clsx(
                                'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border-2 transition-all',
                                accentColor === 'purple'
                                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                                    : 'border-brand-200 dark:border-brand-800 hover:border-brand-300 dark:hover:border-brand-600'
                            )}
                        >
                            <span className="w-4 h-4 rounded-full bg-gradient-to-br from-purple-400 to-pink-500" />
                            紫粉色
                        </button>
                        <button
                            onClick={() => setAccentColor('cyan')}
                            className={clsx(
                                'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border-2 transition-all',
                                accentColor === 'cyan'
                                    ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-900/20'
                                    : 'border-brand-200 dark:border-brand-800 hover:border-brand-300 dark:hover:border-brand-600'
                            )}
                        >
                            <span className="w-4 h-4 rounded-full bg-gradient-to-br from-cyan-400 to-teal-500" />
                            青绿色
                        </button>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">默认源语言</label>
                    <select className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500">
                        <option value="en">English</option>
                        <option value="zh">中文</option>
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">默认目标语言</label>
                    <select className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500">
                        <option value="zh">中文</option>
                        <option value="en">English</option>
                    </select>
                </div>
            </div>
        </div>
    )
}
