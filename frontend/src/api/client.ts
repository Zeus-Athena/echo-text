/**
 * API Client
 * Axios instance with authentication interceptors
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import type {
    TokenResponse,
    User,
    UserUpdate,
    UserConfigResponse,
    UserConfigUpdate,
    RecordingListItem,
    RecordingDetail,
    RecordingCreate,
    RecordingUpdate,
    TranscriptUpdate,
    TranslationUpdate,
    Folder,
    FolderCreate,
    FolderListResponse,
    Tag,
    TagCreate,
    SearchParams,
    ExportFormat,
    ExportOptions,
    TranslateTextRequest,
    TranslateTextResponse,
    TranslationHistoryItem,
    DictionaryEntry,
    VocabularyItem,
    TTSVoice,
    ConfigTestRequest,
    ConfigTestResponse,
    ShareLinkCreate,
    ShareLink,
    SharedRecording,
    DiarizationRequest,
    AdminCreateUser,
    AdminUpdateUser,
    PromptTemplate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    ProvidersMetadataResponse,
} from './types'


const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export const apiClient = axios.create({
    baseURL: `${API_BASE_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor - add auth token
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

// Response interceptor - handle errors
let isRefreshing = false

apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config

        // Skip auth handling for login/register/refresh requests
        const isAuthRequest = originalRequest?.url?.includes('/auth/')

        if (error.response?.status === 401 && !isAuthRequest) {
            // Check if we're already on login page to avoid redirect loop
            if (window.location.pathname === '/login') {
                return Promise.reject(error)
            }

            // Token expired, try refresh
            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken && !isRefreshing) {
                isRefreshing = true
                try {
                    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
                        refresh_token: refreshToken,
                    })
                    const { access_token, refresh_token } = response.data
                    localStorage.setItem('access_token', access_token)
                    localStorage.setItem('refresh_token', refresh_token)
                    isRefreshing = false

                    // Retry original request
                    if (originalRequest) {
                        originalRequest.headers.Authorization = `Bearer ${access_token}`
                        return axios(originalRequest)
                    }
                } catch {
                    isRefreshing = false
                    // Refresh failed, logout
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    window.location.href = '/login'
                }
            } else if (!refreshToken) {
                window.location.href = '/login'
            }
        }
        return Promise.reject(error)
    }
)

// API functions
export const authApi = {
    register: (data: { email: string; username: string; password: string }) =>
        apiClient.post('/auth/register', data),

    login: (data: { username: string; password: string }) =>
        apiClient.post('/auth/login', data),

    refresh: (refreshToken: string) =>
        apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
}

export const userApi = {
    getMe: () => apiClient.get('/users/me'),
    updateMe: (data: { username?: string; email?: string }) =>
        apiClient.put('/users/me', data),
    changePassword: (data: { current_password: string; new_password: string }) =>
        apiClient.post('/users/me/password', data),
    getConfig: () => apiClient.get('/users/me/config'),
    updateConfig: (data: any) => apiClient.put('/users/me/config', data),
    getBalance: (serviceType: 'llm' | 'stt', provider?: string) =>
        apiClient.get('/users/me/balance', { params: { service_type: serviceType, provider } }),
    listUsers: () => apiClient.get('/users/'),
    createUser: (data: { email: string; username: string; password: string; can_use_admin_key?: boolean }) =>
        apiClient.post('/users/', data),
    updateUser: (userId: string, data: { email?: string; username?: string; password?: string; can_use_admin_key?: boolean }) =>
        apiClient.put(`/users/${userId}`, data),
    deleteUser: (userId: string) => apiClient.delete(`/users/${userId}`),
}

export const recordingsApi = {
    list: (params?: { folder_id?: string; search?: string; source_type?: string; uncategorized?: boolean; skip?: number; limit?: number }) =>
        apiClient.get('/recordings/', { params }),
    get: (id: string) => apiClient.get(`/recordings/${id}`),
    create: (data: { title: string; source_lang?: string; target_lang?: string; folder_id?: string }) =>
        apiClient.post('/recordings/', data),
    update: (id: string, data: { title?: string; folder_id?: string; tag_ids?: string[] }) =>
        apiClient.put(`/recordings/${id}`, data),
    delete: (id: string) => apiClient.delete(`/recordings/${id}`),
    batchDelete: (ids: string[]) => apiClient.post('/recordings/batch/delete', { ids }),
    batchMove: (ids: string[], folder_id: string | null) =>
        apiClient.post('/recordings/batch/move', { ids, folder_id }),

    // Audio upload & STT
    upload: (file: Blob, data: { title?: string; source_lang?: string; target_lang?: string; auto_process?: boolean }) => {
        const formData = new FormData()
        formData.append('file', file, (file as File).name || 'recording.webm')
        if (data.title) formData.append('title', data.title)
        if (data.source_lang) formData.append('source_lang', data.source_lang)
        if (data.target_lang) formData.append('target_lang', data.target_lang)
        if (data.auto_process) formData.append('auto_process', 'true')
        return apiClient.post('/recordings/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    },
    getAudioUrl: (id: string) => `${API_BASE_URL}/api/v1/recordings/${id}/audio`,
    process: (id: string) => apiClient.post(`/recordings/${id}/process`),
    transcribe: (id: string) => apiClient.post(`/recordings/${id}/transcribe`),
    translateRecording: (id: string) => apiClient.post(`/recordings/${id}/translate`),
    summarize: (id: string) => apiClient.post(`/recordings/${id}/summarize`),
    updateTranscript: (id: string, data: { full_text: string; segments?: any[] }) =>
        apiClient.put(`/recordings/${id}/transcript`, data),
    updateTranslation: (id: string, data: { full_text: string; segments?: any[] }) =>
        apiClient.put(`/recordings/${id}/translation`, data),

    // Folders
    listFolders: (params?: { source_type?: string }) => apiClient.get('/recordings/folders', { params }),
    createFolder: (data: { name: string; parent_id?: string; source_type?: string }) =>
        apiClient.post('/recordings/folders', data),
    deleteFolder: (id: string) => apiClient.delete(`/recordings/folders/${id}`),

    // Tags
    listTags: () => apiClient.get('/recordings/tags'),
    createTag: (data: { name: string; color?: string }) =>
        apiClient.post('/recordings/tags', data),
}

export const searchApi = {
    search: (params: { q: string; search_in?: string; limit?: number; offset?: number }) =>
        apiClient.get('/search/', { params }),
}

export const exportApi = {
    exportRecording: (id: string, format: 'markdown' | 'pdf' | 'docx' | 'srt', options?: {
        include_transcript?: boolean;
        include_translation?: boolean;
        include_summary?: boolean;
        include_timestamps?: boolean;
        use_translation?: boolean;
    }) => {
        const params = new URLSearchParams()
        if (options?.include_transcript !== undefined) params.append('include_transcript', String(options.include_transcript))
        if (options?.include_translation !== undefined) params.append('include_translation', String(options.include_translation))
        if (options?.include_summary !== undefined) params.append('include_summary', String(options.include_summary))
        if (options?.include_timestamps !== undefined) params.append('include_timestamps', String(options.include_timestamps))
        if (options?.use_translation !== undefined) params.append('use_translation', String(options.use_translation))

        return apiClient.get(`/export/${id}/${format}`, {
            params,
            responseType: 'blob'
        })
    },

    getExportUrl: (id: string, format: string) =>
        `${API_BASE_URL}/api/v1/export/${id}/${format}`,
}

export const translateApi = {
    translateText: (data: { text: string; source_lang?: string; target_lang?: string; style?: string }) =>
        apiClient.post('/translate/text', data),
    translateTextStream: (data: { text: string; source_lang?: string; target_lang?: string }) =>
        fetch(`${API_BASE_URL}/api/v1/translate/text/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            },
            body: JSON.stringify(data),
        }),
    getHistory: (limit?: number) => apiClient.get('/translate/history', { params: { limit } }),

    // Dictionary
    lookupWord: (word: string, language?: string) =>
        apiClient.get(`/translate/dictionary/${word}`, { params: { language } }),
    getDictionaryHistory: (limit?: number) =>
        apiClient.get('/translate/dictionary/history', { params: { limit } }),
    getVocabulary: () => apiClient.get('/translate/vocabulary'),
    addToVocabulary: (data: { word: string; language?: string }) =>
        apiClient.post('/translate/vocabulary', data),
    removeFromVocabulary: (word: string) =>
        apiClient.delete(`/translate/vocabulary/${word}`),

    // TTS
    tts: (data: { text: string; voice?: string; speed?: number }) =>
        apiClient.post('/translate/tts', data, { responseType: 'blob' }),
    getTTSVoices: () => apiClient.get('/translate/tts/voices'),
}

export const configApi = {
    testLLM: (data: { provider: string; api_key: string; base_url: string; model?: string }) =>
        apiClient.post('/config/test/llm', data),
    testSTT: (data: { provider: string; api_key: string; base_url: string; model?: string }) =>
        apiClient.post('/config/test/stt', data),
    testTTS: (data: { provider: string; api_key?: string; base_url?: string }) =>
        apiClient.post('/config/test/tts', data),
    getSTTModels: () =>
        apiClient.get('/config/test/stt/models'),
    fetchSTTModels: (data: { provider: string; api_key: string; base_url: string }) =>
        apiClient.post('/config/test/stt/models/fetch', data),
    // New: Get providers metadata (single source of truth)
    getProviders: () =>
        apiClient.get<ProvidersMetadataResponse>('/config/providers'),
}


export const shareApi = {
    create: (data: {
        recording_id: string;
        expires_in_hours?: number;
        max_views?: number;
        include_audio?: boolean;
        include_translation?: boolean;
        include_summary?: boolean;
        password?: string;
    }) => apiClient.post('/share/', data),

    getRecordingLinks: (recordingId: string) =>
        apiClient.get(`/share/recording/${recordingId}`),

    revoke: (linkId: string) =>
        apiClient.delete(`/share/${linkId}`),

    // Public access (no auth required)
    accessShared: (token: string, password?: string) =>
        apiClient.get(`/share/access/${token}`, { params: { password } }),

    getShareAudioUrl: (token: string, password?: string) => {
        const baseUrl = API_BASE_URL || window.location.origin
        return `${baseUrl}/api/v1/share/access/${token}/audio${password ? `?password=${encodeURIComponent(password)}` : ''}`
    },
}

export const diarizationApi = {
    runDiarization: (recordingId: string, options?: {
        provider?: 'assemblyai' | 'deepgram';
        expected_speakers?: number;
    }) => apiClient.post(`/diarization/${recordingId}`, options || {}),

    getProviders: () => apiClient.get('/diarization/providers'),
}

export const promptsApi = {
    list: (type?: string) => apiClient.get<PromptTemplate[]>('/prompts/', { params: { template_type: type } }),
    create: (data: PromptTemplateCreate) => apiClient.post<PromptTemplate>('/prompts/', data),
    update: (id: string, data: PromptTemplateUpdate) => apiClient.put<PromptTemplate>(`/prompts/${id}`, data),
    delete: (id: string) => apiClient.delete(`/prompts/${id}`),
}

