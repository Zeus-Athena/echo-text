/**
 * App Store
 * Global app state (theme, settings, etc.)
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'
type AccentColor = 'purple' | 'cyan'

interface AppState {
    theme: Theme
    accentColor: AccentColor
    sidebarOpen: boolean

    // Actions
    setTheme: (theme: Theme) => void
    setAccentColor: (color: AccentColor) => void
    toggleSidebar: () => void
    setSidebarOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>()(
    persist(
        (set) => ({
            theme: 'system',
            accentColor: 'purple',
            sidebarOpen: true,

            setTheme: (theme) => {
                set({ theme })

                // Apply theme to document
                const root = document.documentElement
                if (theme === 'system') {
                    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
                    root.classList.toggle('dark', systemDark)
                } else {
                    root.classList.toggle('dark', theme === 'dark')
                }
            },

            setAccentColor: (accentColor) => {
                set({ accentColor })
                // Apply accent color to document
                const root = document.documentElement
                root.dataset.accent = accentColor
            },

            toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
            setSidebarOpen: (open) => set({ sidebarOpen: open }),
        }),
        {
            name: 'app-storage',
            partialize: (state) => ({
                theme: state.theme,
                accentColor: state.accentColor,
            }),
        }
    )
)

// Initialize theme and accent on load
const initTheme = () => {
    const root = document.documentElement
    const stored = localStorage.getItem('app-storage')

    let theme = 'system'
    let accentColor = 'purple'

    if (stored) {
        try {
            const { state } = JSON.parse(stored)
            theme = state?.theme || 'system'
            accentColor = state?.accentColor || 'purple'
        } catch (e) {
            // ignore parse error
        }
    }

    // Apply theme
    if (theme === 'system') {
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        root.classList.toggle('dark', systemDark)
    } else {
        root.classList.toggle('dark', theme === 'dark')
    }

    // Always apply accent color
    root.dataset.accent = accentColor
}

initTheme()

