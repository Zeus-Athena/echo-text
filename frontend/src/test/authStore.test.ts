/**
 * Auth Store Tests
 * 认证状态管理测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act } from '@testing-library/react'
import { useAuthStore } from '../stores/auth'

describe('useAuthStore', () => {
    beforeEach(() => {
        // Reset store state before each test
        const store = useAuthStore.getState()
        store.logout()
        vi.clearAllMocks()
    })

    describe('initial state', () => {
        it('should have null user initially', () => {
            const { user } = useAuthStore.getState()
            expect(user).toBeNull()
        })

        it('should not be authenticated initially', () => {
            const { isAuthenticated } = useAuthStore.getState()
            expect(isAuthenticated).toBe(false)
        })

        it('should have null tokens initially', () => {
            const { accessToken, refreshToken } = useAuthStore.getState()
            expect(accessToken).toBeNull()
            expect(refreshToken).toBeNull()
        })
    })

    describe('login', () => {
        const mockUser = {
            id: '123',
            email: 'test@example.com',
            username: 'testuser',
            role: 'user' as const,
        }

        it('should set user on login', () => {
            act(() => {
                useAuthStore.getState().login(mockUser, 'access_token', 'refresh_token')
            })

            const { user } = useAuthStore.getState()
            expect(user).toEqual(mockUser)
        })

        it('should set isAuthenticated to true', () => {
            act(() => {
                useAuthStore.getState().login(mockUser, 'access_token', 'refresh_token')
            })

            const { isAuthenticated } = useAuthStore.getState()
            expect(isAuthenticated).toBe(true)
        })

        it('should store tokens', () => {
            act(() => {
                useAuthStore.getState().login(mockUser, 'access_token', 'refresh_token')
            })

            const { accessToken, refreshToken } = useAuthStore.getState()
            expect(accessToken).toBe('access_token')
            expect(refreshToken).toBe('refresh_token')
        })

        it('should save tokens to localStorage', () => {
            act(() => {
                useAuthStore.getState().login(mockUser, 'access_token_123', 'refresh_token_456')
            })

            expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'access_token_123')
            expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'refresh_token_456')
        })
    })

    describe('logout', () => {
        const mockUser = {
            id: '123',
            email: 'test@example.com',
            username: 'testuser',
            role: 'user' as const,
        }

        beforeEach(() => {
            // Login first
            act(() => {
                useAuthStore.getState().login(mockUser, 'token', 'refresh')
            })
        })

        it('should clear user on logout', () => {
            act(() => {
                useAuthStore.getState().logout()
            })

            const { user } = useAuthStore.getState()
            expect(user).toBeNull()
        })

        it('should set isAuthenticated to false', () => {
            act(() => {
                useAuthStore.getState().logout()
            })

            const { isAuthenticated } = useAuthStore.getState()
            expect(isAuthenticated).toBe(false)
        })

        it('should clear tokens', () => {
            act(() => {
                useAuthStore.getState().logout()
            })

            const { accessToken, refreshToken } = useAuthStore.getState()
            expect(accessToken).toBeNull()
            expect(refreshToken).toBeNull()
        })

        it('should remove tokens from localStorage', () => {
            act(() => {
                useAuthStore.getState().logout()
            })

            expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
            expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
        })
    })

    describe('updateUser', () => {
        const mockUser = {
            id: '123',
            email: 'test@example.com',
            username: 'testuser',
            role: 'user' as const,
        }

        it('should update user fields', () => {
            act(() => {
                useAuthStore.getState().login(mockUser, 'token', 'refresh')
            })

            act(() => {
                useAuthStore.getState().updateUser({ username: 'newname' })
            })

            const { user } = useAuthStore.getState()
            expect(user?.username).toBe('newname')
            expect(user?.email).toBe('test@example.com') // Other fields unchanged
        })

        it('should not crash if user is null', () => {
            act(() => {
                useAuthStore.getState().updateUser({ username: 'newname' })
            })

            const { user } = useAuthStore.getState()
            expect(user).toBeNull()
        })

        it('should update email', () => {
            act(() => {
                useAuthStore.getState().login(mockUser, 'token', 'refresh')
            })

            act(() => {
                useAuthStore.getState().updateUser({ email: 'new@example.com' })
            })

            const { user } = useAuthStore.getState()
            expect(user?.email).toBe('new@example.com')
        })
    })
})
