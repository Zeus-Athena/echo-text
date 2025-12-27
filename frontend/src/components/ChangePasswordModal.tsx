/**
 * Change Password Modal Component
 * Modal dialog for changing user password
 */
import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Lock, Eye, EyeOff, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { userApi } from '@/api/client'

interface ChangePasswordModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export default function ChangePasswordModal({ open, onOpenChange }: ChangePasswordModalProps) {
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [showCurrentPassword, setShowCurrentPassword] = useState(false)
    const [showNewPassword, setShowNewPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)

    const resetForm = () => {
        setCurrentPassword('')
        setNewPassword('')
        setConfirmPassword('')
        setShowCurrentPassword(false)
        setShowNewPassword(false)
        setShowConfirmPassword(false)
        setError('')
        setSuccess(false)
    }

    const handleClose = () => {
        resetForm()
        onOpenChange(false)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        // Validation
        if (!currentPassword || !newPassword || !confirmPassword) {
            setError('请填写所有字段')
            return
        }

        if (newPassword.length < 6) {
            setError('新密码至少需要6个字符')
            return
        }

        if (newPassword !== confirmPassword) {
            setError('两次输入的新密码不一致')
            return
        }

        setLoading(true)

        try {
            await userApi.changePassword({
                current_password: currentPassword,
                new_password: newPassword,
            })
            setSuccess(true)
            setTimeout(() => {
                handleClose()
            }, 1500)
        } catch (err: any) {
            if (err.response?.status === 400) {
                setError('当前密码不正确')
            } else {
                setError('修改密码失败，请稍后重试')
            }
        } finally {
            setLoading(false)
        }
    }

    return (
        <Dialog.Root open={open} onOpenChange={onOpenChange}>
            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
                <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md">
                    <div className="bg-brand-50 dark:bg-gray-900 rounded-2xl shadow-2xl border border-brand-100 dark:border-gray-700 overflow-hidden">
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 pb-4">
                            <Dialog.Title className="text-xl font-bold text-gray-900 dark:text-white">
                                修改密码
                            </Dialog.Title>
                            <Dialog.Close asChild>
                                <button
                                    onClick={handleClose}
                                    className="p-1 rounded-lg hover:bg-brand-100 dark:hover:bg-gray-800 transition-colors"
                                >
                                    <X className="w-5 h-5 text-gray-500" />
                                </button>
                            </Dialog.Close>
                        </div>

                        {/* Description */}
                        <Dialog.Description className="px-6 pb-4 text-sm text-gray-600 dark:text-gray-400">
                            如果您是使用初始随机密码登录的，建议您在此修改为自己的密码。
                        </Dialog.Description>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-4">
                            {/* Current Password */}
                            <div>
                                <label className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-2">
                                    <span className="text-red-500 mr-1">*</span>
                                    当前密码
                                </label>
                                <div className="relative">
                                    <div className="absolute left-3 top-1/2 -translate-y-1/2">
                                        <Lock className="w-4 h-4 text-gray-400" />
                                    </div>
                                    <input
                                        type={showCurrentPassword ? 'text' : 'password'}
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        placeholder="请输入当前密码"
                                        className="w-full pl-10 pr-10 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                    >
                                        {showCurrentPassword ? (
                                            <Eye className="w-4 h-4 text-gray-400" />
                                        ) : (
                                            <EyeOff className="w-4 h-4 text-gray-400" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* New Password */}
                            <div>
                                <label className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-2">
                                    <span className="text-red-500 mr-1">*</span>
                                    新密码
                                </label>
                                <div className="relative">
                                    <div className="absolute left-3 top-1/2 -translate-y-1/2">
                                        <Lock className="w-4 h-4 text-gray-400" />
                                    </div>
                                    <input
                                        type={showNewPassword ? 'text' : 'password'}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="请输入新密码"
                                        className="w-full pl-10 pr-10 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowNewPassword(!showNewPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                    >
                                        {showNewPassword ? (
                                            <Eye className="w-4 h-4 text-gray-400" />
                                        ) : (
                                            <EyeOff className="w-4 h-4 text-gray-400" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Confirm Password */}
                            <div>
                                <label className="block text-sm font-medium text-gray-900 dark:text-gray-200 mb-2">
                                    <span className="text-red-500 mr-1">*</span>
                                    确认新密码
                                </label>
                                <div className="relative">
                                    <div className="absolute left-3 top-1/2 -translate-y-1/2">
                                        <Lock className="w-4 h-4 text-gray-400" />
                                    </div>
                                    <input
                                        type={showConfirmPassword ? 'text' : 'password'}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="请输入新密码"
                                        className="w-full pl-10 pr-10 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                                    >
                                        {showConfirmPassword ? (
                                            <Eye className="w-4 h-4 text-gray-400" />
                                        ) : (
                                            <EyeOff className="w-4 h-4 text-gray-400" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Error Message */}
                            {error && (
                                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm">
                                    {error}
                                </div>
                            )}

                            {/* Success Message */}
                            {success && (
                                <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm">
                                    密码修改成功！
                                </div>
                            )}

                            {/* Buttons */}
                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    className="px-6 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors font-medium"
                                >
                                    取 消
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading || success}
                                    className={clsx(
                                        'px-6 py-2.5 rounded-xl font-medium transition-all flex items-center gap-2',
                                        loading || success
                                            ? 'bg-brand-300 dark:bg-brand-700 cursor-not-allowed'
                                            : 'bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25'
                                    )}
                                >
                                    {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                                    确认修改
                                </button>
                            </div>
                        </form>
                    </div>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    )
}
