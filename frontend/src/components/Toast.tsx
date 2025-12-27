/**
 * Toast Component
 * 快速弹窗提示
 */
import { useEffect, useState } from 'react'
import { Check, X, AlertCircle, Info } from 'lucide-react'
import clsx from 'clsx'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastProps {
    message: string
    type?: ToastType
    duration?: number
    onClose: () => void
}

export function Toast({ message, type = 'info', duration = 4000, onClose }: ToastProps) {
    const [isExiting, setIsExiting] = useState(false)

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsExiting(true)
            setTimeout(onClose, 300)
        }, duration)

        return () => clearTimeout(timer)
    }, [duration, onClose])

    const handleClose = () => {
        setIsExiting(true)
        setTimeout(onClose, 300)
    }

    const icons = {
        success: <Check className="w-5 h-5" />,
        error: <X className="w-5 h-5" />,
        warning: <AlertCircle className="w-5 h-5" />,
        info: <Info className="w-5 h-5" />,
    }

    const colors = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-amber-500 text-white',
        info: 'bg-blue-500 text-white',
    }


    return (
        <div
            className={clsx(
                'fixed z-50 flex items-center gap-2 px-4 py-2.5 rounded-lg shadow-lg max-w-sm',
                'left-1/2 top-6 -translate-x-1/2',
                'transition-all duration-300 ease-out',
                colors[type],
                isExiting ? 'opacity-0 -translate-y-4' : 'opacity-100 translate-y-0'
            )}
        >
            {icons[type]}
            <span className="flex-1 text-sm font-medium">{message}</span>
            <button
                onClick={handleClose}
                className="ml-2 p-1 rounded-full hover:bg-white/20 transition-colors"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    )
}

// Toast Manager Hook
interface ToastItem {
    id: number
    message: string
    type: ToastType
}

let toastId = 0

export function useToast() {
    const [toasts, setToasts] = useState<ToastItem[]>([])

    const show = (message: string, type: ToastType = 'info') => {
        const id = ++toastId
        setToasts(prev => [...prev, { id, message, type }])
    }

    const remove = (id: number) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }

    const success = (message: string) => show(message, 'success')
    const error = (message: string) => show(message, 'error')
    const warning = (message: string) => show(message, 'warning')
    const info = (message: string) => show(message, 'info')

    const ToastContainer = () => (
        <div className="fixed inset-0 z-50 pointer-events-none flex items-center justify-center">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    onClose={() => remove(toast.id)}
                />
            ))}
        </div>
    )

    return { success, error, warning, info, show, ToastContainer }
}
