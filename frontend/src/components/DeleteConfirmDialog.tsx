import { Loader2 } from 'lucide-react'

interface DeleteConfirmDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title?: string;
    description?: string;
    isLoading?: boolean;
}

export function DeleteConfirmDialog({
    isOpen,
    onClose,
    onConfirm,
    title = '确认删除',
    description = '确定要删除吗？此操作不可恢复。',
    isLoading = false
}: DeleteConfirmDialogProps) {
    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4 animate-in zoom-in-95 duration-200 border border-brand-200 dark:border-brand-800">
                <h3 className="text-lg font-semibold mb-2 text-brand-900 dark:text-brand-100">{title}</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-6 leading-relaxed">
                    {description}
                </p>
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        disabled={isLoading}
                        className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition-colors text-sm font-medium"
                    >
                        取消
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={isLoading}
                        className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors flex items-center gap-2 text-sm font-medium shadow-sm shadow-red-200 dark:shadow-none"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '确认删除'}
                    </button>
                </div>
            </div>
        </div>
    )
}
