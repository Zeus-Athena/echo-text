
import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { userApi } from '@/api/client'
import { useToast } from '@/components/Toast'
import { Save, Loader2 } from 'lucide-react'

export function AccountSettings() {
    const { user, updateUser } = useAuthStore()
    const toast = useToast()
    const [username, setUsername] = useState(user?.username || '')
    const [saving, setSaving] = useState(false)

    const handleSave = async () => {
        setSaving(true)
        try {
            await userApi.updateMe({ username })
            updateUser({ username })
            toast.success('✅ 账户信息已保存')
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || '保存失败')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="card p-6 border border-brand-200 dark:border-brand-800 shadow-sm">
            <toast.ToastContainer />
            <h2 className="text-lg font-semibold mb-6 text-brand-700 dark:text-brand-300">账户设置</h2>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">用户名</label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">邮箱</label>
                    <input
                        type="email"
                        value={user?.email || ''}
                        disabled
                        className="input bg-gray-50 dark:bg-gray-800 border-brand-200 dark:border-brand-800"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">角色</label>
                    <input
                        type="text"
                        value={user?.role === 'admin' ? '管理员' : '普通用户'}
                        disabled
                        className="input bg-gray-50 dark:bg-gray-800 border-brand-200 dark:border-brand-800"
                    />
                </div>

                <div className="pt-2">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="btn-primary"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        保存
                    </button>
                </div>
            </div>
        </div>
    )
}
