/**
 * Unit tests for timestamp precision logic in useRealtimeSTT
 * Tests the findTimeAtPosition algorithm used for precise segment splitting
 */

import { describe, it, expect } from 'vitest'

// Simulate the TimestampedChunk interface
interface TimestampedChunk {
    text: string
    start: number
    end: number
    charOffset: number
}

/**
 * findTimeAtPosition - extracted for testing
 * This is a pure function version of the logic in useRealtimeSTT
 */
function findTimeAtPosition(
    charPos: number,
    chunks: TimestampedChunk[],
    textLength: number,
    segmentStart: number,
    segmentEnd: number
): number {
    if (chunks.length === 0) {
        // Fallback to simple ratio calculation
        const ratio = charPos / textLength
        return segmentStart + (segmentEnd - segmentStart) * ratio
    }

    // Find the chunk containing this character position
    let targetChunk: TimestampedChunk | null = null
    for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i]
        const chunkEnd = chunk.charOffset + chunk.text.length
        if (charPos >= chunk.charOffset && charPos < chunkEnd) {
            targetChunk = chunk
            break
        }
        // If charPos is in the gap between chunks (spaces), use previous chunk's end time
        if (i < chunks.length - 1 && charPos >= chunkEnd && charPos < chunks[i + 1].charOffset) {
            return chunk.end
        }
    }

    if (targetChunk) {
        // Interpolate within the chunk
        const posInChunk = charPos - targetChunk.charOffset
        const ratio = posInChunk / targetChunk.text.length
        return targetChunk.start + (targetChunk.end - targetChunk.start) * ratio
    }

    // If beyond all chunks, return last chunk's end time
    if (chunks.length > 0) {
        return chunks[chunks.length - 1].end
    }

    return segmentEnd
}

describe('findTimeAtPosition', () => {
    describe('with no chunks (fallback)', () => {
        it('should use simple ratio calculation', () => {
            const time = findTimeAtPosition(50, [], 100, 0, 10)
            expect(time).toBe(5) // 50% of 10 seconds
        })

        it('should handle start position', () => {
            const time = findTimeAtPosition(0, [], 100, 0, 10)
            expect(time).toBe(0)
        })

        it('should handle end position', () => {
            const time = findTimeAtPosition(100, [], 100, 0, 10)
            expect(time).toBe(10)
        })
    })

    describe('with single chunk', () => {
        const chunks: TimestampedChunk[] = [
            { text: 'Hello world', start: 0, end: 2, charOffset: 0 }
        ]

        it('should interpolate within chunk', () => {
            // Position 5 is roughly middle of "Hello world" (11 chars)
            const time = findTimeAtPosition(5, chunks, 11, 0, 2)
            expect(time).toBeCloseTo(0.909, 2) // 5/11 * 2
        })

        it('should return start at position 0', () => {
            const time = findTimeAtPosition(0, chunks, 11, 0, 2)
            expect(time).toBe(0)
        })
    })

    describe('with multiple chunks', () => {
        // Simulate: "Hello world. How are you?" 
        // Chunk 1: "Hello world." (0-12) at time 0-3s
        // Chunk 2: "How are you?" (13-25) at time 3-6s
        const chunks: TimestampedChunk[] = [
            { text: 'Hello world.', start: 0, end: 3, charOffset: 0 },
            { text: 'How are you?', start: 3, end: 6, charOffset: 13 }
        ]

        it('should use correct chunk for position in first chunk', () => {
            const time = findTimeAtPosition(6, chunks, 25, 0, 6)
            // Position 6 in "Hello world." (12 chars), ratio = 6/12 = 0.5
            // Time = 0 + 3 * 0.5 = 1.5
            expect(time).toBeCloseTo(1.5, 2)
        })

        it('should use correct chunk for position in second chunk', () => {
            const time = findTimeAtPosition(19, chunks, 25, 0, 6)
            // Position 19 is at charOffset 13, so posInChunk = 19 - 13 = 6
            // "How are you?" has 12 chars, ratio = 6/12 = 0.5
            // Time = 3 + 3 * 0.5 = 4.5
            expect(time).toBeCloseTo(4.5, 2)
        })

        it('should return previous chunk end for gap between chunks', () => {
            // Position 12 is after first chunk but before second (the space)
            const time = findTimeAtPosition(12, chunks, 25, 0, 6)
            expect(time).toBe(3) // End of first chunk
        })

        it('should return last chunk end for position beyond all chunks', () => {
            const time = findTimeAtPosition(30, chunks, 25, 0, 6)
            expect(time).toBe(6) // End of last chunk
        })
    })

    describe('precision improvement scenarios', () => {
        // Real Deepgram scenario: multiple short chunks
        const deepgramChunks: TimestampedChunk[] = [
            { text: 'I learned from', start: 70, end: 73, charOffset: 0 },
            { text: 'the monks but', start: 73, end: 76, charOffset: 15 },
            { text: 'the original', start: 76, end: 79, charOffset: 29 },
            { text: 'airbenders were', start: 79, end: 82, charOffset: 42 },
            { text: 'the sky bison.', start: 82, end: 85, charOffset: 58 },
        ]
        const totalText = 'I learned from the monks but the original airbenders were the sky bison.'

        it('should accurately find time for "monks" position', () => {
            // "monks" starts at position 19 (in chunk 2)
            const time = findTimeAtPosition(19, deepgramChunks, totalText.length, 70, 85)
            // Chunk 2 starts at charOffset 15, so posInChunk = 19 - 15 = 4
            // Chunk 2 has 13 chars, ratio = 4/13 ≈ 0.31
            // Time = 73 + 3 * 0.31 ≈ 73.93
            expect(time).toBeCloseTo(73.92, 1)
        })

        it('should accurately find time for "bison" position', () => {
            // "bison" is near end, around position 66
            const time = findTimeAtPosition(66, deepgramChunks, totalText.length, 70, 85)
            // In chunk 5 (charOffset 58), posInChunk = 66 - 58 = 8
            // Chunk 5 has 14 chars, ratio = 8/14 ≈ 0.57
            // Time = 82 + 3 * 0.57 ≈ 83.7
            expect(time).toBeCloseTo(83.7, 1)
        })
    })

    describe('pseudo-streaming scenario (single chunk)', () => {
        // Groq/OpenAI returns one big chunk per batch
        const groqChunk: TimestampedChunk[] = [
            { text: 'Hello world how are you today I am doing fine thank you for asking.', start: 0, end: 6, charOffset: 0 }
        ]
        const totalText = groqChunk[0].text

        it('should still interpolate within the single chunk', () => {
            // Position at "today" which is around position 25
            const time = findTimeAtPosition(25, groqChunk, totalText.length, 0, 6)
            // ratio = 25/68 ≈ 0.37
            // Time = 0 + 6 * 0.37 ≈ 2.2
            expect(time).toBeCloseTo(2.2, 1)
        })
    })
})
