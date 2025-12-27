/**
 * API Types Tests
 * 前端类型定义测试
 */
import { describe, it, expect } from 'vitest'
import type {
    User,
    RecordingDetail,
    TranscriptSegment,
    WSMessage,
    WSTranscriptMessage,
} from '../api/types'

describe('API Types', () => {
    describe('User type', () => {
        it('should have correct structure', () => {
            const user: User = {
                id: '123',
                email: 'test@example.com',
                username: 'testuser',
                role: 'user',
                is_active: true,
                can_use_admin_key: false,
                created_at: '2024-01-01T00:00:00Z',
            }

            expect(user.id).toBe('123')
            expect(user.role).toBe('user')
        })

        it('should accept admin role', () => {
            const admin: User = {
                id: '456',
                email: 'admin@example.com',
                username: 'admin',
                role: 'admin',
                is_active: true,
                can_use_admin_key: true,
                created_at: '2024-01-01T00:00:00Z',
            }

            expect(admin.role).toBe('admin')
        })
    })

    describe('TranscriptSegment type', () => {
        it('should have correct structure', () => {
            const segment: TranscriptSegment = {
                start: 0.0,
                end: 5.0,
                text: 'Hello world',
            }

            expect(segment.start).toBe(0.0)
            expect(segment.end).toBe(5.0)
            expect(segment.text).toBe('Hello world')
        })

        it('should accept optional speaker', () => {
            const segment: TranscriptSegment = {
                start: 0.0,
                end: 5.0,
                text: 'Hello',
                speaker: 'Speaker 1',
            }

            expect(segment.speaker).toBe('Speaker 1')
        })
    })

    describe('RecordingDetail type', () => {
        it('should have correct structure', () => {
            const recording: RecordingDetail = {
                id: '123',
                title: 'Test Recording',
                s3_key: null,
                audio_url: null,
                audio_format: 'opus',
                audio_size: 1024,
                duration_seconds: 60,
                source_lang: 'en',
                target_lang: 'zh',
                status: 'completed',
                source_type: 'realtime',
                folder_id: null,
                tags: [],
                transcript: null,
                translation: null,
                ai_summary: null,
                created_at: '2024-01-01T00:00:00Z',
                updated_at: '2024-01-01T00:00:00Z',
            }

            expect(recording.id).toBe('123')
            expect(recording.status).toBe('completed')
            expect(recording.audio_format).toBe('opus')
        })
    })

    describe('WebSocket message types', () => {
        it('should correctly type transcript message', () => {
            const msg: WSTranscriptMessage = {
                type: 'transcript',
                text: 'Hello',
                is_final: true,
            }

            expect(msg.type).toBe('transcript')
            expect(msg.is_final).toBe(true)
        })

        it('should discriminate union types', () => {
            const msg: WSMessage = {
                type: 'error',
                message: 'Something went wrong',
            }

            if (msg.type === 'error') {
                expect(msg.message).toBe('Something went wrong')
            }
        })
    })
})
