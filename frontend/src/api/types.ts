/**
 * API Types
 * TypeScript 类型定义 - 与后端 schemas 同步
 */

// ========== Common Types ==========

export type UUID = string

// ========== Auth Types ==========

export interface LoginRequest {
    username: string
    password: string
}

export interface RegisterRequest {
    email: string
    username: string
    password: string
}

export interface TokenResponse {
    access_token: string
    refresh_token: string
    token_type: 'bearer'
}

export interface RefreshTokenRequest {
    refresh_token: string
}

// ========== User Types ==========

export interface User {
    id: UUID
    email: string
    username: string
    role: 'user' | 'admin'
    is_active: boolean
    can_use_admin_key: boolean
    created_at: string
}

export interface UserUpdate {
    username?: string
    email?: string
}

export interface PasswordChange {
    current_password: string
    new_password: string
}

export interface AdminCreateUser {
    email: string
    username: string
    password: string
    can_use_admin_key?: boolean
}

export interface AdminUpdateUser {
    username?: string
    email?: string
    password?: string
    can_use_admin_key?: boolean
}

// ========== User Config Types ==========

export interface LLMConfig {
    provider?: string | null
    api_key?: string | null
    base_url?: string | null
    model?: string | null
    keys?: Record<string, string | null> | null
}

export interface STTConfig {
    provider?: string | null
    api_key?: string | null
    base_url?: string | null
    model?: string | null
    keys?: Record<string, string | null> | null
}

export interface TTSConfig {
    provider: string
    api_key?: string | null
    base_url?: string | null
    voice: string
}

export interface DictConfig {
    provider: string
    api_key?: string | null
}

export interface PreferencesConfig {
    theme: 'system' | 'light' | 'dark'
    default_source_lang: string
    default_target_lang: string
}

export interface RecordingConfig {
    audio_buffer_duration: number
    silence_threshold: number
    silence_mode: 'manual' | 'adaptive'
    silence_prefer_source: 'current' | 'auto'
    silence_threshold_source: 'default' | 'manual' | 'manual_detect' | 'auto'
    translation_mode?: number  // 0=fast mode, 6=throttle mode (for Deepgram)
    segment_soft_threshold?: number
    segment_hard_threshold?: number
}

export interface UserConfigResponse {
    llm: LLMConfig
    stt: STTConfig
    tts: TTSConfig
    dict: DictConfig
    preferences: PreferencesConfig
    recording: RecordingConfig
    using_admin_key: boolean
}

export interface UserConfigUpdate {
    llm?: LLMConfig
    stt?: STTConfig
    tts?: TTSConfig
    dict?: DictConfig
    preferences?: PreferencesConfig
    recording?: RecordingConfig
}

// ========== Folder Types ==========

export interface Folder {
    id: UUID
    name: string
    parent_id: UUID | null
    source_type: 'realtime' | 'upload'
    recording_count: number
    created_at: string
}

export interface FolderCreate {
    name: string
    parent_id?: UUID
    source_type?: 'realtime' | 'upload'
}

export interface FolderListResponse {
    folders: Folder[]
    total_recordings: number
    uncategorized_count: number
}

// ========== Tag Types ==========

export interface Tag {
    id: UUID
    name: string
    color: string
}

export interface TagCreate {
    name: string
    color?: string
}

// ========== Recording Types ==========

export type RecordingStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type SourceType = 'realtime' | 'upload'

export interface TranscriptSegment {
    start: number
    end: number
    text: string
    speaker?: string
    is_final?: boolean
}

export interface Transcript {
    id: UUID
    segments: TranscriptSegment[]
    full_text: string | null
    language: string
    created_at: string
}

export interface Translation {
    id: UUID
    segments: TranscriptSegment[]
    full_text: string | null
    target_lang: string
    llm_model: string | null
    created_at: string
}

export interface AISummary {
    id: UUID
    summary: string | null
    key_points: string[]
    action_items: string[]
    auto_tags: string[]
    chapters: Array<{ timestamp: number; title: string }>
    llm_model: string | null
    created_at: string
}

export interface RecordingListItem {
    id: UUID
    title: string
    duration_seconds: number
    source_lang: string
    target_lang: string
    status: RecordingStatus
    source_type: SourceType
    has_summary: boolean
    tags: Tag[]
    created_at: string
}

export interface RecordingDetail {
    id: UUID
    title: string
    s3_key: string | null
    audio_url: string | null
    audio_format: 'opus' | 'webm' | 'wav'
    audio_size: number | null
    duration_seconds: number
    source_lang: string
    target_lang: string
    status: RecordingStatus
    source_type: SourceType
    folder_id: UUID | null
    tags: Tag[]
    transcript: Transcript | null
    translation: Translation | null
    ai_summary: AISummary | null
    created_at: string
    updated_at: string
}

export interface RecordingCreate {
    title: string
    source_lang?: string
    target_lang?: string
    folder_id?: UUID
}

export interface RecordingUpdate {
    title?: string
    folder_id?: UUID | null
    tag_ids?: UUID[]
}

export interface TranscriptUpdate {
    full_text: string
    segments?: TranscriptSegment[]
}

export interface TranslationUpdate {
    full_text: string
    segments?: TranscriptSegment[]
}

// ========== Batch Operations ==========

export interface BatchDeleteRequest {
    ids: UUID[]
}

export interface BatchMoveRequest {
    ids: UUID[]
    folder_id: UUID | null
}

// ========== Search Types ==========

export interface SearchParams {
    q: string
    search_in?: 'all' | 'title' | 'transcript' | 'translation'
    limit?: number
    offset?: number
}

export interface SearchResult {
    recordings: RecordingListItem[]
    total: number
}

// ========== Export Types ==========

export type ExportFormat = 'markdown' | 'pdf' | 'docx' | 'srt'

export interface ExportOptions {
    include_transcript?: boolean
    include_translation?: boolean
    include_summary?: boolean
    include_timestamps?: boolean
    use_translation?: boolean
}

// ========== Translate Types ==========

export interface TranslateTextRequest {
    text: string
    source_lang?: string
    target_lang?: string
    style?: string
}

export interface TranslateTextResponse {
    translated_text: string
    source_lang: string
    target_lang: string
}

export interface TranslationHistoryItem {
    id: UUID
    source_text: string
    translated_text: string
    source_lang: string
    target_lang: string
    created_at: string
}

// ========== Dictionary Types ==========

export interface DictionaryEntry {
    word: string
    language: string
    pronunciation?: string
    definitions: Array<{
        part_of_speech: string
        meaning: string
        examples?: string[]
    }>
}

export interface VocabularyItem {
    word: string
    language: string
    added_at: string
}

// ========== TTS Types ==========

export interface TTSRequest {
    text: string
    voice?: string
    speed?: number
}

export interface TTSVoice {
    id: string
    name: string
    language: string
    gender?: string
}

// ========== Config Test Types ==========

export interface ConfigTestRequest {
    provider: string
    api_key?: string
    base_url?: string
    model?: string
}

export interface ConfigTestResponse {
    success: boolean
    message: string
    provider: string
    latency_ms?: number
}

// ========== Share Types ==========

export interface ShareLinkCreate {
    recording_id: UUID
    expires_in_hours?: number
    max_views?: number
    include_audio?: boolean
    include_translation?: boolean
    include_summary?: boolean
    password?: string
}

export interface ShareLink {
    id: UUID
    token: string
    recording_id: UUID
    expires_at: string | null
    max_views: number | null
    current_views: number
    include_audio: boolean
    include_translation: boolean
    include_summary: boolean
    is_password_protected: boolean
    created_at: string
}

export interface SharedRecording {
    title: string
    duration_seconds: number
    source_lang: string
    target_lang: string
    has_audio: boolean
    transcript: Transcript | null
    translation: Translation | null
    ai_summary: AISummary | null
}

// ========== Diarization Types ==========

export type DiarizationProvider = 'assemblyai' | 'deepgram'

export interface DiarizationRequest {
    provider?: DiarizationProvider
    expected_speakers?: number
}

export interface DiarizationResult {
    segments: Array<{
        speaker: string
        start: number
        end: number
        text: string
    }>
}

// ========== Prompt Template Types ==========

export interface PromptTemplate {
    id: UUID
    user_id: UUID
    name: string
    template_type: string
    content: string
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface PromptTemplateCreate {
    name: string
    template_type: string
    content: string
    is_active?: boolean
}

export interface PromptTemplateUpdate {
    name?: string
    template_type?: string
    content?: string
    is_active?: boolean
}

// ========== WebSocket Types ==========

export type WSMessageType =
    | 'transcript'
    | 'translation'
    | 'status'
    | 'error'
    | 'pong'
    | 'audio_saved'
    | 'auto_stopped'

export interface WSTranscriptMessage {
    type: 'transcript'
    text: string
    is_final: boolean
    speaker?: string
}

export interface WSTranslationMessage {
    type: 'translation'
    text: string
    is_final: boolean
}

export interface WSStatusMessage {
    type: 'status'
    message: string
}

export interface WSErrorMessage {
    type: 'error'
    message: string
}

export interface WSPongMessage {
    type: 'pong'
}

export interface WSAudioSavedMessage {
    type: 'audio_saved'
    recording_id: string
    audio_size: number
}

export interface WSAutoStoppedMessage {
    type: 'auto_stopped'
    reason: string
}

export type WSMessage =
    | WSTranscriptMessage
    | WSTranslationMessage
    | WSStatusMessage
    | WSErrorMessage
    | WSPongMessage
    | WSAudioSavedMessage
    | WSAutoStoppedMessage

export interface WSStartAction {
    action: 'start'
    source_lang?: string
    target_lang?: string
    recording_id?: string
    diarization?: boolean
    silence_threshold?: number
}

export interface WSStopAction {
    action: 'stop'
}

export interface WSPauseAction {
    action: 'pause'
}

export interface WSResumeAction {
    action: 'resume'
}

export interface WSPingAction {
    action: 'ping'
}

export type WSAction =
    | WSStartAction
    | WSStopAction
    | WSPauseAction
    | WSResumeAction
    | WSPingAction

// ========== API Response Types ==========

export interface APIError {
    detail: string | { msg: string; type: string }[]
}

export interface PaginatedResponse<T> {
    items: T[]
    total: number
    skip: number
    limit: number
}
