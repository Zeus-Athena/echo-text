/**
 * useDebounce Hook Tests
 * 防抖 Hook 测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useDebounce } from '../hooks/useDebounce'

describe('useDebounce', () => {
    beforeEach(() => {
        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('should return initial value immediately', () => {
        const { result } = renderHook(() => useDebounce('initial', 500))
        expect(result.current).toBe('initial')
    })

    it('should debounce value changes', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 500),
            { initialProps: { value: 'initial' } }
        )

        // Change value
        rerender({ value: 'changed' })

        // Immediately, should still be initial
        expect(result.current).toBe('initial')

        // Advance timer by 499ms - should still be initial
        act(() => {
            vi.advanceTimersByTime(499)
        })
        expect(result.current).toBe('initial')

        // Advance timer to exactly 500ms - should update
        act(() => {
            vi.advanceTimersByTime(1)
        })
        expect(result.current).toBe('changed')
    })

    it('should reset timer on rapid value changes', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 500),
            { initialProps: { value: 'initial' } }
        )

        // Change value multiple times quickly
        rerender({ value: 'change1' })
        act(() => {
            vi.advanceTimersByTime(200)
        })

        rerender({ value: 'change2' })
        act(() => {
            vi.advanceTimersByTime(200)
        })

        rerender({ value: 'change3' })
        act(() => {
            vi.advanceTimersByTime(200)
        })

        // Should still be initial (timer reset each time)
        expect(result.current).toBe('initial')

        // After 500ms from last change, should be final value
        act(() => {
            vi.advanceTimersByTime(300)
        })
        expect(result.current).toBe('change3')
    })

    it('should use default delay of 500ms', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value),
            { initialProps: { value: 'initial' } }
        )

        rerender({ value: 'changed' })

        act(() => {
            vi.advanceTimersByTime(499)
        })
        expect(result.current).toBe('initial')

        act(() => {
            vi.advanceTimersByTime(1)
        })
        expect(result.current).toBe('changed')
    })

    it('should work with custom delay', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 100),
            { initialProps: { value: 'initial' } }
        )

        rerender({ value: 'changed' })

        act(() => {
            vi.advanceTimersByTime(99)
        })
        expect(result.current).toBe('initial')

        act(() => {
            vi.advanceTimersByTime(1)
        })
        expect(result.current).toBe('changed')
    })

    it('should work with objects', () => {
        const initial = { name: 'initial' }
        const changed = { name: 'changed' }

        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 500),
            { initialProps: { value: initial } }
        )

        rerender({ value: changed })

        act(() => {
            vi.advanceTimersByTime(500)
        })

        expect(result.current).toEqual(changed)
    })

    it('should work with numbers', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 500),
            { initialProps: { value: 0 } }
        )

        rerender({ value: 42 })

        act(() => {
            vi.advanceTimersByTime(500)
        })

        expect(result.current).toBe(42)
    })

    it('should cleanup timer on unmount', () => {
        const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')

        const { unmount, rerender } = renderHook(
            ({ value }) => useDebounce(value, 500),
            { initialProps: { value: 'initial' } }
        )

        rerender({ value: 'changed' })
        unmount()

        expect(clearTimeoutSpy).toHaveBeenCalled()
    })
})
