
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth'
import { userApi } from '@/api/client'
import { useToast } from '@/components/Toast'
import { User, Loader2 } from 'lucide-react'
import clsx from 'clsx'

export function UserManagement() {
    const queryClient = useQueryClient()
    const toast = useToast()
    const { user: currentUser } = useAuthStore()

    // Modal states
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [showEditModal, setShowEditModal] = useState(false)
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

    // Form data
    const [newUser, setNewUser] = useState({ email: '', username: '', password: '', can_use_admin_key: false })
    const [editUser, setEditUser] = useState<{ id: string; email: string; username: string; password: string; can_use_admin_key: boolean } | null>(null)
    const [deleteUserId, setDeleteUserId] = useState<string | null>(null)

    // Loading states
    const [creating, setCreating] = useState(false)
    const [updating, setUpdating] = useState(false)
    const [deleting, setDeleting] = useState(false)

    const { data: users, isLoading } = useQuery({
        queryKey: ['users'],
        queryFn: () => userApi.listUsers(),
        select: (res) => res.data,
    })

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newUser.email || !newUser.username || !newUser.password) {
            toast.error('请填写所有字段')
            return
        }
        if (newUser.password.length < 6) {
            toast.error('密码至少需要6个字符')
            return
        }

        setCreating(true)
        try {
            await userApi.createUser(newUser)
            toast.success('✅ 用户创建成功')
            queryClient.invalidateQueries({ queryKey: ['users'] })
            setShowCreateModal(false)
            setNewUser({ email: '', username: '', password: '', can_use_admin_key: false })
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || '创建失败')
        } finally {
            setCreating(false)
        }
    }

    const handleEditUser = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!editUser) return

        if (editUser.password && editUser.password.length < 6) {
            toast.error('密码至少需要6个字符')
            return
        }

        setUpdating(true)
        try {
            const updateData: any = {}
            if (editUser.username) updateData.username = editUser.username
            if (editUser.email) updateData.email = editUser.email
            if (editUser.password) updateData.password = editUser.password
            updateData.can_use_admin_key = editUser.can_use_admin_key

            await userApi.updateUser(editUser.id, updateData)
            toast.success('✅ 用户信息已更新')
            queryClient.invalidateQueries({ queryKey: ['users'] })
            setShowEditModal(false)
            setEditUser(null)
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || '更新失败')
        } finally {
            setUpdating(false)
        }
    }

    const handleDeleteUser = async () => {
        if (!deleteUserId) return

        setDeleting(true)
        try {
            await userApi.deleteUser(deleteUserId)
            toast.success('✅ 用户已删除')
            queryClient.invalidateQueries({ queryKey: ['users'] })
            setShowDeleteConfirm(false)
            setDeleteUserId(null)
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || '删除失败')
        } finally {
            setDeleting(false)
        }
    }

    const openEditModal = (u: any) => {
        setEditUser({ id: u.id, email: u.email, username: u.username, password: '', can_use_admin_key: u.can_use_admin_key || false })
        setShowEditModal(true)
    }

    const openDeleteConfirm = (userId: string) => {
        setDeleteUserId(userId)
        setShowDeleteConfirm(true)
    }

    if (isLoading) {
        return <div className="card p-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
    }

    return (
        <div className="card border border-brand-200 dark:border-brand-800 shadow-sm overflow-hidden">
            <toast.ToastContainer />
            <div className="p-4 border-b border-brand-100 dark:border-brand-800 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/50">
                <h2 className="text-lg font-semibold text-brand-700 dark:text-brand-300">用户管理</h2>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="btn-primary text-sm shadow-sm"
                >
                    + 新建用户
                </button>
            </div>

            <div className="divide-y divide-gray-200 dark:divide-gray-800">
                {users?.map((u: any) => (
                    <div key={u.id} className="flex items-center gap-4 p-4">
                        <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                            <User className="w-5 h-5 text-gray-500" />
                        </div>
                        <div className="flex-1">
                            <p className="font-medium">{u.username}</p>
                            <p className="text-sm text-gray-500">{u.email}</p>
                        </div>
                        <span className={clsx(
                            'px-2 py-1 rounded text-xs',
                            u.role === 'admin'
                                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                        )}>
                            {u.role === 'admin' ? '管理员' : '普通用户'}
                        </span>
                        {u.id !== currentUser?.id && (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => openEditModal(u)}
                                    className="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    编辑
                                </button>
                                <button
                                    onClick={() => openDeleteConfirm(u.id)}
                                    className="px-3 py-1.5 text-xs rounded-lg text-red-600 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
                                >
                                    删除
                                </button>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Create User Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4 border border-brand-200 dark:border-brand-800">
                        <h3 className="text-lg font-semibold mb-4 text-brand-700 dark:text-brand-300">新建用户</h3>
                        <form onSubmit={handleCreateUser} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1.5">邮箱</label>
                                <input
                                    type="email"
                                    value={newUser.email}
                                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    placeholder="user@example.com"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1.5">用户名</label>
                                <input
                                    type="text"
                                    value={newUser.username}
                                    onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    placeholder="2-100个字符"
                                    required
                                    minLength={2}
                                    maxLength={100}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1.5">密码</label>
                                <input
                                    type="password"
                                    value={newUser.password}
                                    onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    placeholder="6-100个字符"
                                    required
                                    minLength={6}
                                    maxLength={100}
                                />
                            </div>
                            <div className="flex items-center gap-3">
                                <input
                                    type="checkbox"
                                    id="create-can-use-admin-key"
                                    checked={newUser.can_use_admin_key}
                                    onChange={(e) => setNewUser({ ...newUser, can_use_admin_key: e.target.checked })}
                                    className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                                />
                                <label htmlFor="create-can-use-admin-key" className="text-sm">允许使用管理员 API Key</label>
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowCreateModal(false)
                                        setNewUser({ email: '', username: '', password: '', can_use_admin_key: false })
                                    }}
                                    className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                                >
                                    取消
                                </button>
                                <button
                                    type="submit"
                                    disabled={creating}
                                    className="btn-primary"
                                >
                                    {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : '创建用户'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit User Modal */}
            {showEditModal && editUser && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4 border border-brand-200 dark:border-brand-800">
                        <h3 className="text-lg font-semibold mb-4 text-brand-700 dark:text-brand-300">编辑用户</h3>
                        <form onSubmit={handleEditUser} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1.5">邮箱</label>
                                <input
                                    type="email"
                                    value={editUser.email}
                                    onChange={(e) => setEditUser({ ...editUser, email: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    placeholder="user@example.com"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1.5">用户名</label>
                                <input
                                    type="text"
                                    value={editUser.username}
                                    onChange={(e) => setEditUser({ ...editUser, username: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    placeholder="2-100个字符"
                                    minLength={2}
                                    maxLength={100}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1.5">新密码（留空则不修改）</label>
                                <input
                                    type="password"
                                    value={editUser.password}
                                    onChange={(e) => setEditUser({ ...editUser, password: e.target.value })}
                                    className="input border-brand-200 dark:border-brand-800 focus:border-brand-500 focus:ring-brand-500"
                                    placeholder="6-100个字符"
                                    minLength={6}
                                    maxLength={100}
                                />
                            </div>
                            <div className="flex items-center gap-3">
                                <input
                                    type="checkbox"
                                    id="edit-can-use-admin-key"
                                    checked={editUser.can_use_admin_key}
                                    onChange={(e) => setEditUser({ ...editUser, can_use_admin_key: e.target.checked })}
                                    className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                                />
                                <label htmlFor="edit-can-use-admin-key" className="text-sm">允许使用管理员 API Key</label>
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowEditModal(false)
                                        setEditUser(null)
                                    }}
                                    className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                                >
                                    取消
                                </button>
                                <button
                                    type="submit"
                                    disabled={updating}
                                    className="btn-primary"
                                >
                                    {updating ? <Loader2 className="w-4 h-4 animate-spin" /> : '保存修改'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
                        <h3 className="text-lg font-semibold mb-2">确认删除</h3>
                        <p className="text-gray-600 dark:text-gray-400 text-sm mb-6">
                            确定要删除该用户吗？此操作不可恢复。
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setShowDeleteConfirm(false)
                                    setDeleteUserId(null)
                                }}
                                className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleDeleteUser}
                                disabled={deleting}
                                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
                            >
                                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : '确认删除'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
