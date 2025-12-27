/**
 * Main Layout Component
 * Top navigation and page outlet
 */
import { useState, useRef, useEffect } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import {
    Home,
    Mic,
    Languages,
    AudioWaveform,
    BookOpen,
    Settings,
    LogOut,
    Sun,
    Moon,
    User,
    KeyRound,
} from 'lucide-react'
import clsx from 'clsx'
import ChangePasswordModal from '@/components/ChangePasswordModal'

// Injected by Vite at build time
declare const __APP_VERSION__: string

const navigation = [
    { name: '首页', href: '/', icon: Home },
    { name: '实时转录', href: '/recordings', icon: Mic },
    { name: '文本翻译', href: '/text-translate', icon: Languages },
    { name: '语音翻译', href: '/voice-translate', icon: AudioWaveform },
    { name: '词典', href: '/dictionary', icon: BookOpen },
    { name: '设置', href: '/settings', icon: Settings },
]

export default function Layout() {
    const { user, logout } = useAuthStore()
    const { theme, setTheme } = useAppStore()
    const navigate = useNavigate()
    const [showUserMenu, setShowUserMenu] = useState(false)
    const [showPasswordModal, setShowPasswordModal] = useState(false)
    const menuTimeoutRef = useRef<number | null>(null)

    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (menuTimeoutRef.current) {
                clearTimeout(menuTimeoutRef.current)
            }
        }
    }, [])

    const handleMouseEnter = () => {
        // Clear any pending hide timeout
        if (menuTimeoutRef.current) {
            clearTimeout(menuTimeoutRef.current)
            menuTimeoutRef.current = null
        }
        setShowUserMenu(true)
    }

    const handleMouseLeave = () => {
        // Delay hiding the menu to give user time to move to it
        menuTimeoutRef.current = window.setTimeout(() => {
            setShowUserMenu(false)
        }, 200) // 200ms delay before hiding
    }

    const handleLogout = () => {
        setShowUserMenu(false)
        logout()
        navigate('/login')
    }

    const handleChangePassword = () => {
        setShowUserMenu(false)
        setShowPasswordModal(true)
    }

    const toggleTheme = () => {
        setTheme(theme === 'dark' ? 'light' : 'dark')
    }

    return (
        <div className="min-h-screen bg-[var(--app-bg)] transition-colors duration-300">
            {/* Top Navigation */}
            <header className="sticky top-0 z-50 w-full border-b border-brand-200/60 dark:border-brand-800/60 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg">
                <div className="flex h-14 items-center px-4 lg:px-6">
                    {/* Logo */}
                    <div className="flex items-center gap-2 mr-6">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
                            <Mic className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-bold text-lg hidden sm:block">EchoText</span>
                    </div>

                    {/* Navigation Links */}
                    <nav className="flex items-center gap-1">
                        {navigation.map((item) => (
                            <NavLink
                                key={item.href}
                                to={item.href}
                                end={item.href === '/'}
                                className={({ isActive }) =>
                                    clsx(
                                        'flex items-center gap-2 px-3 py-2 rounded-lg text-base font-semibold transition-colors',
                                        isActive
                                            ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
                                            : 'text-gray-900 hover:text-black hover:bg-gray-100 dark:text-white dark:hover:text-white dark:hover:bg-gray-800'
                                    )
                                }
                            >
                                <item.icon className="w-4 h-4" />
                                <span className="hidden md:block">{item.name}</span>
                            </NavLink>
                        ))}
                    </nav>

                    {/* Right Side */}
                    <div className="ml-auto flex items-center gap-3">
                        {/* Version */}
                        <span className="text-xs text-gray-400 hidden lg:block">
                            v{__APP_VERSION__}
                        </span>

                        {/* User Menu with Hover Dropdown */}
                        <div
                            className="relative"
                            onMouseEnter={handleMouseEnter}
                            onMouseLeave={handleMouseLeave}
                        >
                            <div className="flex items-center gap-2 cursor-pointer p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                                <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                                    <User className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                                </div>
                                <div className="hidden sm:block">
                                    <p className="text-sm font-medium">{user?.username}</p>
                                    <p className="text-xs text-gray-500">
                                        {user?.role === 'admin' ? '管理员' : '普通用户'}
                                    </p>
                                </div>
                            </div>

                            {/* Dropdown Menu */}
                            {showUserMenu && (
                                <div
                                    className="absolute right-0 top-full mt-2 w-44 py-2 bg-brand-50 dark:bg-gray-800 rounded-2xl shadow-xl border border-brand-200 dark:border-brand-800 z-50"
                                    onMouseEnter={handleMouseEnter}
                                    onMouseLeave={handleMouseLeave}
                                >
                                    <button
                                        onClick={handleChangePassword}
                                        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-brand-100 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <KeyRound className="w-4 h-4" />
                                        修改密码
                                    </button>
                                    <button
                                        onClick={handleLogout}
                                        className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 dark:text-gray-200 hover:bg-brand-100 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <LogOut className="w-4 h-4" />
                                        退出登录
                                    </button>
                                </div>
                            )}
                        </div>

                        {/* Theme Toggle */}
                        <button
                            onClick={toggleTheme}
                            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                        >
                            {theme === 'dark' ? (
                                <Sun className="w-4 h-4" />
                            ) : (
                                <Moon className="w-4 h-4" />
                            )}
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1">
                <Outlet />
            </main>

            {/* Change Password Modal */}
            <ChangePasswordModal
                open={showPasswordModal}
                onOpenChange={setShowPasswordModal}
            />
        </div>
    )
}
