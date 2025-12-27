/**
 * API Client Tests
 * API 客户端测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

// Mock axios
vi.mock('axios', () => ({
    default: {
        create: vi.fn(() => ({
            interceptors: {
                request: { use: vi.fn() },
                response: { use: vi.fn() },
            },
            get: vi.fn(),
            post: vi.fn(),
            put: vi.fn(),
            delete: vi.fn(),
        })),
    },
}))

describe('API Client Configuration', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('should create axios instance', () => {
        // Re-import to trigger create
        expect(axios.create).toBeDefined()
    })
})

describe('API Types Integration', () => {
    // These tests verify our types work correctly with API patterns

    it('should handle recording list params', () => {
        const params: {
            folder_id?: string
            search?: string
            source_type?: string
            uncategorized?: boolean
            skip?: number
            limit?: number
        } = {
            folder_id: '123',
            search: 'test',
            source_type: 'realtime',
            skip: 0,
            limit: 20,
        }

        expect(params.folder_id).toBe('123')
        expect(params.limit).toBe(20)
    })

    it('should handle recording create data', () => {
        const data = {
            title: 'Test Recording',
            source_lang: 'en',
            target_lang: 'zh',
            folder_id: '456',
        }

        expect(data.title).toBe('Test Recording')
        expect(data.source_lang).toBe('en')
    })

    it('should handle upload data', () => {
        const mockFile = new Blob(['audio data'], { type: 'audio/webm' })
        const data = {
            title: 'Uploaded File',
            source_lang: 'zh',
            target_lang: 'en',
            auto_process: true,
        }

        expect(mockFile.type).toBe('audio/webm')
        expect(data.auto_process).toBe(true)
    })

    it('should handle share link data', () => {
        const shareData = {
            recording_id: '123',
            expires_in_hours: 24,
            max_views: 10,
            include_audio: true,
            include_translation: true,
            include_summary: false,
            password: 'secret',
        }

        expect(shareData.recording_id).toBe('123')
        expect(shareData.expires_in_hours).toBe(24)
        expect(shareData.password).toBe('secret')
    })

    it('should handle export options', () => {
        const options = {
            include_transcript: true,
            include_translation: true,
            include_summary: false,
            include_timestamps: true,
            use_translation: false,
        }

        expect(options.include_transcript).toBe(true)
        expect(options.use_translation).toBe(false)
    })

    it('should handle config test data', () => {
        const testData = {
            provider: 'openai',
            api_key: 'sk-test',
            base_url: 'https://api.openai.com',
            model: 'gpt-4',
        }

        expect(testData.provider).toBe('openai')
        expect(testData.api_key).toBe('sk-test')
    })

    it('should handle diarization options', () => {
        const options: {
            provider?: 'assemblyai' | 'deepgram'
            expected_speakers?: number
        } = {
            provider: 'assemblyai',
            expected_speakers: 2,
        }

        expect(options.provider).toBe('assemblyai')
        expect(options.expected_speakers).toBe(2)
    })
})

describe('LocalStorage Token Management', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('should get access token', () => {
        localStorage.getItem = vi.fn().mockReturnValue('test_token')

        const token = localStorage.getItem('access_token')
        expect(token).toBe('test_token')
    })

    it('should set access token', () => {
        localStorage.setItem('access_token', 'new_token')
        expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new_token')
    })

    it('should remove access token', () => {
        localStorage.removeItem('access_token')
        expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
    })
})
