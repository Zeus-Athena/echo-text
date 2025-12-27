
export function UsageStats() {
    return (
        <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm">
            <h2 className="text-lg font-semibold mb-6 text-brand-700 dark:text-brand-300">用量统计</h2>

            <div className="space-y-6">
                <div>
                    <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-700 dark:text-gray-300">录音时长</span>
                        <span className="font-medium">120 / 300 分钟</span>
                    </div>
                    <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden border border-brand-100 dark:border-brand-900/30">
                        <div className="h-full w-2/5 bg-brand-500 rounded-full" />
                    </div>
                </div>

                <div>
                    <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-700 dark:text-gray-300">翻译字数</span>
                        <span className="font-medium">45,230 / 100,000 字</span>
                    </div>
                    <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden border border-brand-100 dark:border-brand-900/30">
                        <div className="h-full w-[45%] bg-green-500 rounded-full" />
                    </div>
                </div>

                <div>
                    <div className="flex justify-between text-sm mb-2">
                        <span className="text-gray-700 dark:text-gray-300">TTS 字数</span>
                        <span className="font-medium">12,500 / 50,000 字</span>
                    </div>
                    <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden border border-brand-100 dark:border-brand-900/30">
                        <div className="h-full w-1/4 bg-purple-500 rounded-full" />
                    </div>
                </div>
            </div>
        </div>
    )
}
