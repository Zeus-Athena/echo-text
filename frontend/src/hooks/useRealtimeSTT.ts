/**
 * useRealtimeSTT Hook
 * Real-time Speech-to-Text via WebSocket
 */
import { useState, useRef, useCallback, useEffect } from 'react'

// Dynamically determine WebSocket URL based on current page location
const getWsBaseUrl = () => {
    // Standard relative path strategy: use current protocol and host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}`
}

export interface Segment {
    id?: string
    text: string
    translation: string
    start: number
    end: number
    speaker?: string
    isFinal?: boolean
}

export interface RealtimeSTTState {
    isConnected: boolean
    isRecording: boolean
    transcript: string
    translation: string
    // Interim states for true streaming (gray text)
    interimTranscript: string
    interimTranslation: string
    error: string | null
    duration: number
    currentVolume: number // 0-100 for visualization
    connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
    reconnectAttempts: number
    segments: Segment[]
}

export interface UseRealtimeSTTOptions {
    silenceThreshold?: number // 0-100 (user-facing)
    bufferDuration?: number   // seconds (3-10)
    maxReconnectAttempts?: number // Max attempts before giving up
    reconnectDelay?: number   // Base delay in ms (will use exponential backoff)
    heartbeatInterval?: number // Heartbeat interval in ms
    isPaused?: boolean // Whether recording is paused (stop sending chunks)
    segmentSoftThreshold?: number
    segmentHardThreshold?: number
}

interface UseRealtimeSTTReturn extends RealtimeSTTState {
    startRecording: (sourceLang?: string, targetLang?: string, recordingId?: string) => Promise<void>
    stopRecording: () => Promise<{
        transcript: string;
        translation: string;
        segments: Segment[]
    }>
    resetState: () => void
}

// Chunk with timestamp for precise segment splitting
interface TimestampedChunk {
    text: string
    start: number
    end: number
    charOffset: number  // Character offset in accumulated transcript
}

export function useRealtimeSTT(options: UseRealtimeSTTOptions = {}): UseRealtimeSTTReturn {
    const {
        silenceThreshold = 30,
        maxReconnectAttempts = 100,
        reconnectDelay = 1000,
        heartbeatInterval = 5000,  // 5s heartbeat for faster disconnect detection
        isPaused = false,
        segmentSoftThreshold = 50,
        segmentHardThreshold = 100
    } = options

    // Use refs for segment thresholds to ensure they update when config loads
    const segmentSoftThresholdRef = useRef(segmentSoftThreshold)
    const segmentHardThresholdRef = useRef(segmentHardThreshold)
    useEffect(() => {
        segmentSoftThresholdRef.current = segmentSoftThreshold
        segmentHardThresholdRef.current = segmentHardThreshold
    }, [segmentSoftThreshold, segmentHardThreshold])

    // Use ref for isPaused to access in callbacks without stale closure
    const isPausedRef = useRef(isPaused)
    const prevIsPausedRef = useRef(isPaused)
    useEffect(() => {
        isPausedRef.current = isPaused

        // Send pause/resume action to backend when paused state changes
        const ws = wsRef.current
        if (ws && ws.readyState === WebSocket.OPEN && prevIsPausedRef.current !== isPaused) {
            if (isPaused) {
                ws.send(JSON.stringify({ action: 'pause' }))
                console.log('[STT] Sent pause action')
            } else {
                ws.send(JSON.stringify({ action: 'resume' }))
                console.log('[STT] Sent resume action')
            }
        }
        prevIsPausedRef.current = isPaused
    }, [isPaused])

    // Non-linear mapping: user 0-100 -> RMS threshold
    // Using exponential curve for better UX
    // 0 -> 0 (most sensitive), 50 -> ~15, 100 -> ~60 (most noise resistant)
    const actualThreshold = Math.pow(silenceThreshold / 100, 1.5) * 60

    const [state, setState] = useState<RealtimeSTTState>({
        isConnected: false,
        isRecording: false,
        transcript: '',
        translation: '',
        interimTranscript: '',
        interimTranslation: '',
        error: null,
        duration: 0,
        currentVolume: 0,
        connectionStatus: 'disconnected',
        reconnectAttempts: 0,
        segments: [],
    })

    const wsRef = useRef<WebSocket | null>(null)
    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const streamRef = useRef<MediaStream | null>(null)
    const timerRef = useRef<number | null>(null)
    const transcriptRef = useRef<string>('')
    const translationRef = useRef<string>('')
    const stateRef = useRef(state) // Track state for stopRecording
    const recordingStartTimeRef = useRef<number>(0) // 录音开始时间
    const segmentStartTimeRef = useRef<number>(0)   // 当前 segment 开始时间（后端精确时间戳，秒）
    const segmentEndTimeRef = useRef<number>(0)     // 当前 segment 结束时间（后端精确时间戳，秒）
    const pendingTranslationRef = useRef<boolean>(false) // 是否有待等待的译文
    const timestampedChunksRef = useRef<TimestampedChunk[]>([])  // 保存每个 STT 事件的时间戳信息

    // Flag to track if we are in "Backend Splitting" mode (detected via segment_id)
    const isBackendSplittingRef = useRef<boolean>(false)

    // === 新增: transcript_id 关联机制 (Legacy Mode) ===
    // 存储待翻译的 transcript_id 列表（按顺序）
    const pendingTranscriptIdsRef = useRef<string[]>([])
    // 存储 transcript_id -> 转录文本的映射
    const transcriptIdToTextRef = useRef<Map<string, string>>(new Map())
    // 存储已完成的翻译 (按 transcript_id)
    const completedTranslationsRef = useRef<Map<string, string>>(new Map())
    // 当前 segment 包含的 transcript_ids
    const currentSegmentTranscriptIdsRef = useRef<string[]>([])
    // transcript_id -> segment 索引的映射（用于翻译到达时更新正确的 segment）
    const transcriptIdToSegmentIndexRef = useRef<Map<string, number>>(new Map())

    // Keep stateRef in sync
    useEffect(() => {
        stateRef.current = state
    }, [state])

    // Check if we need to start a new segment (Legacy Mode Only)
    // 软阈值开始找标点，硬上限强制切
    const checkAndSegment = useCallback(() => {
        // Only run in Legacy Mode
        if (isBackendSplittingRef.current) return

        const text = transcriptRef.current
        if (!text.trim()) return

        // Simple word count estimate (split by space)
        const wordCount = text.split(/\s+/).length

        // (findTimeAtPosition Logic - Omitted for brevity in backend mode but needed for legacy)
        // Leaving legacy heavy logic here...

        // 混合方案：超过软阈值后，等文本结尾是句末标点时再切分
        const endsWithPunctuation = /[.!?。！？]$/.test(text.trim())

        if ((wordCount > segmentSoftThresholdRef.current && endsWithPunctuation) || wordCount > segmentHardThresholdRef.current) {
            const startTime = segmentStartTimeRef.current
            const endTime = segmentEndTimeRef.current

            // 保存当前 segment 的 transcriptIds
            const segmentTranscriptIds = [...currentSegmentTranscriptIdsRef.current]

            // 计算该 segment 已有的翻译（根据 transcript_id 收集）
            let segmentTranslation = segmentTranscriptIds
                .map(id => completedTranslationsRef.current.get(id) || '')
                .filter(t => t)
                .join(' ')

            // 如果按 transcript_id 收集不到翻译，使用当前显示的翻译作为回退
            if (!segmentTranslation && translationRef.current) {
                segmentTranslation = translationRef.current
            }

            const newSegment: Segment = {
                text: transcriptRef.current,
                translation: segmentTranslation,
                start: startTime,
                end: endTime,
                isFinal: true
            }

            // 记录 transcriptIds 属于哪个 segment（用于后续翻译到达时更新）
            setState(prev => {
                const newIndex = prev.segments.length
                segmentTranscriptIds.forEach(id => {
                    transcriptIdToSegmentIndexRef.current.set(id, newIndex)
                })
                return {
                    ...prev,
                    segments: [...prev.segments, newSegment],
                    transcript: '',
                    translation: ''
                }
            })

            // Reset for next segment
            transcriptRef.current = ''
            translationRef.current = ''
            segmentStartTimeRef.current = endTime
            currentSegmentTranscriptIdsRef.current = []
            timestampedChunksRef.current = []  // 清空所有 chunks
        }
    }, [])

    // VAD refs
    const audioContextRef = useRef<AudioContext | null>(null)
    const analyserRef = useRef<AnalyserNode | null>(null)
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
    const maxVolumeRef = useRef<number>(0)
    const vadIntervalRef = useRef<number | null>(null)

    // Reconnection refs
    const reconnectTimeoutRef = useRef<number | null>(null)
    const heartbeatIntervalRef = useRef<number | null>(null)
    const lastPongTimeRef = useRef<number>(Date.now())  // Track last pong received
    const pongTimeoutRef = useRef<number | null>(null)  // Timeout to detect dead connection
    const shouldReconnectRef = useRef<boolean>(false)
    const currentSourceLangRef = useRef<string>('en')
    const currentTargetLangRef = useRef<string>('zh')
    const currentRecordingIdRef = useRef<string | undefined>(undefined)
    const currentSilenceThresholdRef = useRef<number>(silenceThreshold)
    const lastChunkIndexRef = useRef<number>(0)  // Track last processed chunk for resume

    // Heartbeat function
    const startHeartbeat = useCallback((ws: WebSocket) => {
        if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current)
        }
        if (pongTimeoutRef.current) {
            clearTimeout(pongTimeoutRef.current)
        }

        // Reset pong time on start
        lastPongTimeRef.current = Date.now()

        heartbeatIntervalRef.current = window.setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: 'ping' }))
                // console.log('[Heartbeat] Sent ping')

                // Set timeout to detect dead connection (5s after ping)
                pongTimeoutRef.current = window.setTimeout(() => {
                    const timeSinceLastPong = Date.now() - lastPongTimeRef.current
                    if (timeSinceLastPong > 8000) {
                        console.warn('[Heartbeat] No pong received, connection appears dead')
                        setState(prev => ({
                            ...prev,
                            connectionStatus: 'reconnecting',
                        }))
                        ws.close()
                    }
                }, 5000)
            }
        }, heartbeatInterval)
    }, [heartbeatInterval])

    const stopHeartbeat = useCallback(() => {
        if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current)
            heartbeatIntervalRef.current = null
        }
        if (pongTimeoutRef.current) {
            clearTimeout(pongTimeoutRef.current)
            pongTimeoutRef.current = null
        }
    }, [])

    // Connect to WebSocket
    const connect = useCallback(async (): Promise<WebSocket> => {
        const token = localStorage.getItem('access_token')
        if (!token) {
            throw new Error('Not authenticated')
        }

        setState(prev => ({
            ...prev,
            connectionStatus: 'connecting',
            error: null
        }))

        return new Promise((resolve, reject) => {
            const ws = new WebSocket(`${getWsBaseUrl()}/api/v1/ws/transcribe/v2/${token}`)

            const connectionTimeout = window.setTimeout(() => {
                if (ws.readyState !== WebSocket.OPEN) {
                    ws.close()
                    reject(new Error('Connection timed out'))
                }
            }, 5000)

            ws.onopen = () => {
                clearTimeout(connectionTimeout)
                setState(prev => ({
                    ...prev,
                    isConnected: true,
                    error: null,
                    connectionStatus: 'connected',
                    reconnectAttempts: 0
                }))
                startHeartbeat(ws)
                resolve(ws)
            }

            ws.onerror = (error) => {
                console.error('WebSocket error:', error)
            }

            ws.onclose = (event) => {
                stopHeartbeat()
                setState(prev => ({ ...prev, isConnected: false }))
                if (event.code !== 1000) {
                    // Unexpected disconnection
                    if (shouldReconnectRef.current) {
                        setState(prev => ({
                            ...prev,
                            connectionStatus: 'disconnected',
                            error: '网络连接断开，录音已保存',
                        }))
                        shouldReconnectRef.current = false
                    } else {
                        setState(prev => ({
                            ...prev,
                            connectionStatus: 'disconnected',
                            error: '连接断开',
                        }))
                    }
                } else {
                    setState(prev => ({ ...prev, connectionStatus: 'disconnected' }))
                }
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)

                    if (data.type === 'transcript') {
                        // === New Backend-Driven Mode Check ===
                        if (data.segment_id) {
                            isBackendSplittingRef.current = true

                            if (data.is_final) {
                                // Accumulate transcript
                                setState(prev => {
                                    const index = prev.segments.findIndex(s => s.id === data.segment_id)
                                    const newSegments = [...prev.segments]

                                    if (index !== -1) {
                                        // Update existing
                                        const seg = newSegments[index]
                                        // Assuming data.text is a chunk (Deepgram) so we append
                                        // But if backend sends full, we replace. New V2 flow sends chunks for transcript event.
                                        newSegments[index] = {
                                            ...seg,
                                            text: seg.text + data.text,
                                            end: data.end_time || seg.end
                                        }
                                    } else {
                                        // Create new
                                        newSegments.push({
                                            id: data.segment_id,
                                            text: data.text,
                                            translation: '',
                                            start: data.start_time || prev.duration,
                                            end: data.end_time || prev.duration,
                                            isFinal: false
                                        })
                                    }
                                    return {
                                        ...prev,
                                        segments: newSegments,
                                        interimTranscript: ''
                                    }
                                })
                            } else {
                                // Interim
                                setState(prev => ({ ...prev, interimTranscript: data.text }))
                            }
                        } else {
                            // === Legacy Mode ===
                            if (isBackendSplittingRef.current) return

                            if (data.is_final) {
                                const prefix = transcriptRef.current ? ' ' : ''
                                const speakerPrefix = data.speaker ? `[${data.speaker}] ` : ''
                                transcriptRef.current += prefix + speakerPrefix + data.text

                                if (data.start_time !== undefined && segmentStartTimeRef.current === 0) {
                                    segmentStartTimeRef.current = data.start_time
                                }
                                if (data.end_time !== undefined) {
                                    segmentEndTimeRef.current = data.end_time
                                }

                                pendingTranslationRef.current = true
                                setState(prev => ({
                                    ...prev,
                                    transcript: transcriptRef.current,
                                    interimTranscript: ''
                                }))

                                const wordCount = transcriptRef.current.split(/\s+/).length
                                if (wordCount > segmentHardThresholdRef.current) {
                                    checkAndSegment()
                                }
                            } else {
                                setState(prev => ({ ...prev, interimTranscript: data.text }))
                            }
                        }

                        if (data.chunk_index !== undefined) {
                            lastChunkIndexRef.current = data.chunk_index
                        }

                    } else if (data.type === 'translation') {
                        if (data.segment_id) {
                            // === Backend Driven Mode ===
                            // Update translation for segment
                            setState(prev => {
                                const index = prev.segments.findIndex(s => s.id === data.segment_id)
                                if (index !== -1) {
                                    const newSegments = [...prev.segments]
                                    const seg = newSegments[index]
                                    const prefix = seg.translation ? ' ' : ''
                                    newSegments[index] = {
                                        ...seg,
                                        translation: seg.translation + prefix + data.text
                                    }
                                    return { ...prev, segments: newSegments }
                                }
                                return prev
                            })
                        } else {
                            // === Legacy Mode ===
                            if (data.is_final) {
                                if (data.transcript_id) {
                                    completedTranslationsRef.current.set(data.transcript_id, data.text)
                                    const idx = pendingTranscriptIdsRef.current.indexOf(data.transcript_id)
                                    if (idx !== -1) pendingTranscriptIdsRef.current.splice(idx, 1)

                                    const segmentIndex = transcriptIdToSegmentIndexRef.current.get(data.transcript_id)
                                    if (segmentIndex !== undefined) {
                                        setState(prev => {
                                            const newSegments = [...prev.segments]
                                            if (newSegments[segmentIndex]) {
                                                const existing = newSegments[segmentIndex].translation
                                                newSegments[segmentIndex] = {
                                                    ...newSegments[segmentIndex],
                                                    translation: existing ? existing + ' ' + data.text : data.text
                                                }
                                            }
                                            return { ...prev, segments: newSegments }
                                        })
                                        return
                                    }
                                }

                                translationRef.current += (translationRef.current ? ' ' : '') + data.text
                                if (pendingTranscriptIdsRef.current.length === 0) pendingTranslationRef.current = false
                                setState(prev => ({
                                    ...prev,
                                    translation: translationRef.current,
                                    interimTranslation: ''
                                }))
                                checkAndSegment()
                            } else {
                                setState(prev => ({ ...prev, interimTranslation: data.text }))
                            }
                        }

                    } else if (data.type === 'segment_complete') {
                        // === Backend Driven Finalize ===
                        if (data.segment_id) {
                            setState(prev => {
                                const index = prev.segments.findIndex(s => s.id === data.segment_id)
                                const newSegments = [...prev.segments]
                                if (index !== -1) {
                                    // Update with final text/time
                                    newSegments[index] = {
                                        ...newSegments[index],
                                        text: data.text,
                                        start: data.start,
                                        end: data.end,
                                        isFinal: true
                                    }
                                } else {
                                    // Add if missing
                                    newSegments.push({
                                        id: data.segment_id,
                                        text: data.text,
                                        translation: '',
                                        start: data.start,
                                        end: data.end,
                                        isFinal: true
                                    })
                                }
                                return { ...prev, segments: newSegments }
                            })
                        }

                    } else if (data.type === 'error') {
                        console.error('WebSocket error:', data.message)
                        setState(prev => ({ ...prev, error: data.message }))
                    } else if (data.type === 'pong') {
                        lastPongTimeRef.current = Date.now()
                    } else if (data.type === 'resumed') {
                        lastChunkIndexRef.current = data.chunk_index || 0
                        setState(prev => ({
                            ...prev,
                            isRecording: true,
                            connectionStatus: 'connected',
                        }))
                    } else if (data.type === 'session_expired') {
                        shouldReconnectRef.current = false
                        setState(prev => ({
                            ...prev,
                            error: 'Recording session expired',
                            isRecording: false,
                        }))
                    } else if (data.type === 'auto_stopped') {
                        shouldReconnectRef.current = false
                        setState(prev => ({
                            ...prev,
                            error: '录制已自动结束',
                            isRecording: false,
                        }))
                    }
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e)
                }
            }

            wsRef.current = ws
        })
    }, [maxReconnectAttempts, reconnectDelay, startHeartbeat, stopHeartbeat, checkAndSegment])

    const startRecording = useCallback(async (sourceLang = 'en', targetLang = 'zh', recordingId?: string) => {
        try {
            currentSourceLangRef.current = sourceLang
            currentTargetLangRef.current = targetLang
            currentRecordingIdRef.current = recordingId
            currentSilenceThresholdRef.current = silenceThreshold
            shouldReconnectRef.current = true

            // Reset state
            transcriptRef.current = ''
            translationRef.current = ''
            isBackendSplittingRef.current = false // Reset mode assumption

            const now = Date.now()
            recordingStartTimeRef.current = now
            segmentStartTimeRef.current = 0
            segmentEndTimeRef.current = 0
            timestampedChunksRef.current = []

            pendingTranscriptIdsRef.current = []
            transcriptIdToTextRef.current.clear()
            completedTranslationsRef.current.clear()
            currentSegmentTranscriptIdsRef.current = []
            transcriptIdToSegmentIndexRef.current.clear()

            setState(prev => ({
                ...prev,
                transcript: '',
                translation: '',
                interimTranscript: '',
                interimTranslation: '',
                error: null,
                duration: 0,
                reconnectAttempts: 0,
                segments: [],
            }))

            const ws = await connect()

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            })
            streamRef.current = stream

            const audioContext = new AudioContext()
            const analyser = audioContext.createAnalyser()
            const source = audioContext.createMediaStreamSource(stream)
            source.connect(analyser)
            analyser.fftSize = 256

            audioContextRef.current = audioContext
            analyserRef.current = analyser
            sourceRef.current = source
            maxVolumeRef.current = 0

            vadIntervalRef.current = window.setInterval(() => {
                const dataArray = new Uint8Array(analyser.frequencyBinCount)
                analyser.getByteTimeDomainData(dataArray)
                let sum = 0
                for (let i = 0; i < dataArray.length; i++) {
                    const x = dataArray[i] - 128
                    sum += x * x
                }
                const rms = Math.sqrt(sum / dataArray.length)
                if (rms > maxVolumeRef.current) {
                    maxVolumeRef.current = rms
                }
                const normalizedVolume = Math.min(100, Math.round((rms / 60) * 100))
                setState(prev => ({ ...prev, currentVolume: normalizedVolume }))
            }, 50)

            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm'

            const mediaRecorder = new MediaRecorder(stream, { mimeType })
            mediaRecorderRef.current = mediaRecorder

            mediaRecorder.ondataavailable = (e) => {
                if (isPausedRef.current) return
                const activeWs = wsRef.current
                if (e.data.size > 0 && activeWs && activeWs.readyState === WebSocket.OPEN) {
                    maxVolumeRef.current = 0
                    activeWs.send(e.data)
                }
            }

            mediaRecorder.start(500)

            ws.send(JSON.stringify({
                action: 'start',
                source_lang: sourceLang,
                target_lang: targetLang,
                recording_id: recordingId,
                silence_threshold: silenceThreshold,
            }))

            const startTime = Date.now()
            timerRef.current = window.setInterval(() => {
                setState(prev => ({
                    ...prev,
                    duration: Math.floor((Date.now() - startTime) / 1000)
                }))
            }, 1000)

            setState(prev => ({ ...prev, isRecording: true }))

        } catch (err) {
            const error = err instanceof Error ? err.message : '录音启动失败'
            setState(prev => ({ ...prev, error }))
            throw new Error(error)
        }
    }, [connect, silenceThreshold])

    const stopRecording = useCallback(async () => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }
        if (vadIntervalRef.current) {
            clearInterval(vadIntervalRef.current)
            vadIntervalRef.current = null
        }
        if (sourceRef.current) sourceRef.current.disconnect()
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close()
        }
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop()
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop())
            streamRef.current = null
        }

        shouldReconnectRef.current = false
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
            reconnectTimeoutRef.current = null
        }
        stopHeartbeat()

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ action: 'stop' }))
            await new Promise(resolve => setTimeout(resolve, 2000))
            wsRef.current.close(1000, 'Recording stopped')
        }

        setState(prev => ({ ...prev, isRecording: false, connectionStatus: 'disconnected' }))

        // Finalize segments
        const finalSegments = [...stateRef.current.segments]

        // Only do manual flush if NOT in backend splitting mode
        if (!isBackendSplittingRef.current && transcriptRef.current.trim()) {
            const lastSegmentDuration = (Date.now() - recordingStartTimeRef.current) / 1000
            const startTime = segmentStartTimeRef.current
            const endTime = Math.max(segmentEndTimeRef.current, lastSegmentDuration)

            finalSegments.push({
                text: transcriptRef.current,
                translation: translationRef.current,
                start: startTime,
                end: endTime,
                isFinal: true
            })
        }

        const fullTranscript = finalSegments.map(s => s.text).join('\n\n')
        const fullTranslation = finalSegments.map(s => s.translation).filter(Boolean).join('\n\n')

        return {
            transcript: fullTranscript,
            translation: fullTranslation,
            segments: finalSegments
        }
    }, [stopHeartbeat])

    const resetState = useCallback(() => {
        transcriptRef.current = ''
        translationRef.current = ''
        shouldReconnectRef.current = false
        timestampedChunksRef.current = []
        isBackendSplittingRef.current = false

        pendingTranscriptIdsRef.current = []
        transcriptIdToTextRef.current.clear()
        completedTranslationsRef.current.clear()
        currentSegmentTranscriptIdsRef.current = []
        transcriptIdToSegmentIndexRef.current.clear()

        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
            reconnectTimeoutRef.current = null
        }

        setState({
            isConnected: false,
            isRecording: false,
            transcript: '',
            translation: '',
            interimTranscript: '',
            interimTranslation: '',
            error: null,
            duration: 0,
            currentVolume: 0,
            connectionStatus: 'disconnected',
            reconnectAttempts: 0,
            segments: [],
        })
    }, [])

    useEffect(() => {
        return () => {
            shouldReconnectRef.current = false
            if (timerRef.current) clearInterval(timerRef.current)
            if (vadIntervalRef.current) clearInterval(vadIntervalRef.current)
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
            if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current)
            if (streamRef.current) streamRef.current.getTracks().forEach(track => track.stop())
            if (wsRef.current) wsRef.current.close(1000, 'Component unmounted')
            if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
                audioContextRef.current.close()
            }
        }
    }, [])

    return {
        ...state,
        startRecording,
        stopRecording,
        resetState,
    }
}
