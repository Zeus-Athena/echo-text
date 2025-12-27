/**
 * Settings Page
 * 设置页
 */
import { Routes, Route, NavLink } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import {
    User,
    Key,
    Palette,
    BarChart3,
    Users,
    Mic,
} from 'lucide-react'
import clsx from 'clsx'

// Import sub-components
import { AccountSettings } from './settings/AccountSettings'
import { APISettings } from './settings/APISettings'
import { PreferencesSettings } from './settings/PreferencesSettings'
import { RecordingSettings } from './settings/RecordingSettings'
import { UsageStats } from './settings/UsageStats'
import { UserManagement } from './settings/UserManagement'

const settingsNav = [
    { name: '账户', href: '/settings', icon: User, end: true },
    { name: 'AI配置', href: '/settings/api', icon: Key },
    { name: '偏好设置', href: '/settings/preferences', icon: Palette },
    { name: '录音设置', href: '/settings/recording', icon: Mic },
    { name: '用量统计', href: '/settings/usage', icon: BarChart3 },
]

function SettingsLayout() {
    const { user } = useAuthStore()

    return (
        <div className="px-4 lg:px-8 py-6 max-w-7xl mx-auto">
            {/* Horizontal Tabs */}
            <nav className="flex gap-1 mb-6 border-b border-gray-200 dark:border-gray-700 overflow-x-auto pb-px">
                {settingsNav.map((item) => (
                    <NavLink
                        key={item.href}
                        to={item.href}
                        end={item.end}
                        className={({ isActive }) =>
                            clsx(
                                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors',
                                isActive
                                    ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                            )
                        }
                    >
                        <item.icon className="w-4 h-4" />
                        {item.name}
                    </NavLink>
                ))}

                {user?.role === 'admin' && (
                    <NavLink
                        to="/settings/users"
                        className={({ isActive }) =>
                            clsx(
                                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors',
                                isActive
                                    ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                            )
                        }
                    >
                        <Users className="w-4 h-4" />
                        用户管理
                    </NavLink>
                )}
            </nav>

            {/* Content */}
            <div>
                <Routes>
                    <Route index element={<AccountSettings />} />
                    <Route path="api" element={<APISettings />} />
                    <Route path="preferences" element={<PreferencesSettings />} />
                    <Route path="recording" element={<RecordingSettings />} />
                    <Route path="usage" element={<UsageStats />} />
                    <Route path="users" element={<UserManagement />} />
                </Routes>
            </div>
        </div>
    )
}

export default function SettingsPage() {
    return <SettingsLayout />
}
