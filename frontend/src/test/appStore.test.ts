/**
 * App Store Tests
 * 应用状态管理测试
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { act } from '@testing-library/react'
import { useAppStore } from '../stores/app'

describe('useAppStore', () => {
    // Mock document for theme tests
    const mockClassList = {
        toggle: vi.fn(),
        add: vi.fn(),
        remove: vi.fn(),
    }
    const mockDataset: Record<string, string> = {}

    beforeEach(() => {
        // Reset store
        act(() => {
            useAppStore.setState({
                theme: 'system',
                accentColor: 'purple',
                sidebarOpen: true,
            })
        })
        vi.clearAllMocks()

        // Mock document.documentElement
        Object.defineProperty(document, 'documentElement', {
            value: {
                classList: mockClassList,
                dataset: mockDataset,
            },
            writable: true,
        })
    })

    describe('initial state', () => {
        it('should have system as default theme', () => {
            const { theme } = useAppStore.getState()
            expect(theme).toBe('system')
        })

        it('should have purple as default accent color', () => {
            const { accentColor } = useAppStore.getState()
            expect(accentColor).toBe('purple')
        })

        it('should have sidebar open by default', () => {
            const { sidebarOpen } = useAppStore.getState()
            expect(sidebarOpen).toBe(true)
        })
    })

    describe('setTheme', () => {
        it('should set theme to light', () => {
            act(() => {
                useAppStore.getState().setTheme('light')
            })

            const { theme } = useAppStore.getState()
            expect(theme).toBe('light')
        })

        it('should set theme to dark', () => {
            act(() => {
                useAppStore.getState().setTheme('dark')
            })

            const { theme } = useAppStore.getState()
            expect(theme).toBe('dark')
        })

        it('should set theme to system', () => {
            act(() => {
                useAppStore.getState().setTheme('dark')
                useAppStore.getState().setTheme('system')
            })

            const { theme } = useAppStore.getState()
            expect(theme).toBe('system')
        })

        it('should toggle dark class for dark theme', () => {
            act(() => {
                useAppStore.getState().setTheme('dark')
            })

            expect(mockClassList.toggle).toHaveBeenCalledWith('dark', true)
        })

        it('should toggle dark class for light theme', () => {
            act(() => {
                useAppStore.getState().setTheme('light')
            })

            expect(mockClassList.toggle).toHaveBeenCalledWith('dark', false)
        })
    })

    describe('setAccentColor', () => {
        it('should set accent color to purple', () => {
            act(() => {
                useAppStore.getState().setAccentColor('purple')
            })

            const { accentColor } = useAppStore.getState()
            expect(accentColor).toBe('purple')
        })

        it('should set accent color to cyan', () => {
            act(() => {
                useAppStore.getState().setAccentColor('cyan')
            })

            const { accentColor } = useAppStore.getState()
            expect(accentColor).toBe('cyan')
        })

        it('should update document dataset', () => {
            act(() => {
                useAppStore.getState().setAccentColor('cyan')
            })

            expect(mockDataset.accent).toBe('cyan')
        })
    })

    describe('sidebar', () => {
        it('should toggle sidebar', () => {
            const initial = useAppStore.getState().sidebarOpen

            act(() => {
                useAppStore.getState().toggleSidebar()
            })

            expect(useAppStore.getState().sidebarOpen).toBe(!initial)
        })

        it('should toggle sidebar back', () => {
            act(() => {
                useAppStore.getState().toggleSidebar()
                useAppStore.getState().toggleSidebar()
            })

            expect(useAppStore.getState().sidebarOpen).toBe(true)
        })

        it('should set sidebar open', () => {
            act(() => {
                useAppStore.getState().setSidebarOpen(false)
            })

            expect(useAppStore.getState().sidebarOpen).toBe(false)
        })

        it('should set sidebar closed', () => {
            act(() => {
                useAppStore.getState().setSidebarOpen(false)
                useAppStore.getState().setSidebarOpen(true)
            })

            expect(useAppStore.getState().sidebarOpen).toBe(true)
        })
    })
})
