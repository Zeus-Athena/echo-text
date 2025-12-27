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

interface RealtimeSTTState {
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
    segments: { text: string; translation: string; start: number; end: number; speaker?: string }[]
}

interface UseRealtimeSTTOptions {
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
        segments: { text: string; translation: string; start: number; end: number }[]
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

    // Keep stateRef in sync
    useEffect(() => {
        stateRef.current = state
    }, [state])

    // Check if we need to start a new segment
    // 软阈值开始找标点，硬上限强制切
    const checkAndSegment = useCallback(() => {
        // 如果还有待等待的译文，不切分（避免译文错位）
        if (pendingTranslationRef.current) {
            return
        }

        const text = transcriptRef.current
        if (!text.trim()) return

        // Simple word count estimate (split by space)
        const wordCount = text.split(/\s+/).length

        /**
         * 根据字符位置查找精确时间
         * 使用 timestampedChunksRef 定位到正确的 chunk，然后在该 chunk 内插值
         */
        const findTimeAtPosition = (charPos: number): number => {
            const chunks = timestampedChunksRef.current
            if (chunks.length === 0) {
                // 没有 chunk 信息，回退到简单比例计算
                const ratio = charPos / text.length
                return segmentStartTimeRef.current +
                    (segmentEndTimeRef.current - segmentStartTimeRef.current) * ratio
            }

            // 找到包含该字符位置的 chunk
            let targetChunk: TimestampedChunk | null = null
            for (let i = 0; i < chunks.length; i++) {
                const chunk = chunks[i]
                const chunkEnd = chunk.charOffset + chunk.text.length
                if (charPos >= chunk.charOffset && charPos < chunkEnd) {
                    targetChunk = chunk
                    break
                }
                // 如果字符位置在 chunks 之间的空隙（空格），使用上一个 chunk 的结束时间
                if (i < chunks.length - 1 && charPos >= chunkEnd && charPos < chunks[i + 1].charOffset) {
                    return chunk.end
                }
            }

            if (targetChunk) {
                // 在该 chunk 内插值
                const posInChunk = charPos - targetChunk.charOffset
                const ratio = posInChunk / targetChunk.text.length
                return targetChunk.start + (targetChunk.end - targetChunk.start) * ratio
            }

            // 如果超出所有 chunks，返回最后一个 chunk 的结束时间
            if (chunks.length > 0) {
                return chunks[chunks.length - 1].end
            }

            // 最终回退
            return segmentEndTimeRef.current
        }

        /**
         * 清理已使用的 chunks（切分后移除已保存的部分）
         */
        const clearUsedChunks = (splitCharPos: number) => {
            const chunks = timestampedChunksRef.current
            // 找到第一个在切分点之后开始的 chunk
            let firstRemainingIdx = chunks.length
            for (let i = 0; i < chunks.length; i++) {
                if (chunks[i].charOffset >= splitCharPos) {
                    firstRemainingIdx = i
                    break
                }
            }
            // 保留剩余的 chunks，并更新它们的 charOffset
            const remainingChunks = chunks.slice(firstRemainingIdx).map(chunk => ({
                ...chunk,
                charOffset: chunk.charOffset - splitCharPos
            }))
            timestampedChunksRef.current = remainingChunks
        }

        // 软阈值：超过设定词数开始找标点切分
        if (wordCount > segmentSoftThreshold) {
            // 查找最后一个句末标点
            const sentenceEnders = /[.!?。！？]/g
            let lastMatch = null
            let match
            while ((match = sentenceEnders.exec(text)) !== null) {
                lastMatch = match
            }

            // 如果找到标点且在文本后半部分，在标点处切分
            if (lastMatch && lastMatch.index > text.length * 0.5) {
                const splitIndex = lastMatch.index + 1
                const segmentText = text.slice(0, splitIndex).trim()
                const remainingText = text.slice(splitIndex).trim()

                // 使用 chunk 精确定位切分时间
                const startTime = segmentStartTimeRef.current
                const splitTime = findTimeAtPosition(splitIndex)

                const newSegment = {
                    text: segmentText,
                    translation: translationRef.current,
                    start: startTime,
                    end: splitTime
                }

                // Reset for next segment
                transcriptRef.current = remainingText
                translationRef.current = ''
                segmentStartTimeRef.current = splitTime
                clearUsedChunks(splitIndex)

                setState(prev => ({
                    ...prev,
                    segments: [...prev.segments, newSegment],
                    transcript: remainingText,
                    translation: ''
                }))
                return
            }
        }

        // 硬上限：超过设定上限强制切分
        if (wordCount > segmentHardThreshold) {
            const startTime = segmentStartTimeRef.current
            const endTime = segmentEndTimeRef.current

            const newSegment = {
                text: transcriptRef.current,
                translation: translationRef.current,
                start: startTime,
                end: endTime
            }

            // Reset for next segment
            transcriptRef.current = ''
            translationRef.current = ''
            segmentStartTimeRef.current = endTime
            timestampedChunksRef.current = []  // 清空所有 chunks

            setState(prev => ({
                ...prev,
                segments: [...prev.segments, newSegment],
                transcript: '',
                translation: ''
            }))
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
                console.log('[Heartbeat] Sent ping')

                // Set timeout to detect dead connection (5s after ping)
                pongTimeoutRef.current = window.setTimeout(() => {
                    const timeSinceLastPong = Date.now() - lastPongTimeRef.current
                    // If no pong received in 8 seconds, consider dead
                    if (timeSinceLastPong > 8000) {
                        console.warn('[Heartbeat] No pong received, connection appears dead')
                        setState(prev => ({
                            ...prev,
                            connectionStatus: 'reconnecting',
                        }))
                        // Close the WebSocket to trigger reconnection
                        ws.close()
                    }
                }, 5000)  // Check 5s after sending ping
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

    // Connect to WebSocket with reconnection support
    const connect = useCallback(async (isReconnect = false): Promise<WebSocket> => {
        const token = localStorage.getItem('access_token')
        if (!token) {
            throw new Error('Not authenticated')
        }

        setState(prev => ({
            ...prev,
            connectionStatus: isReconnect ? 'reconnecting' : 'connecting',
            error: null
        }))

        return new Promise((resolve, reject) => {
            // Use V2 endpoint for Strategy Pattern architecture
            const ws = new WebSocket(`${getWsBaseUrl()}/api/v1/ws/transcribe/v2/${token}`)

            // Force fail if connection takes too long
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

                // Start heartbeat
                startHeartbeat(ws)

                // If reconnecting during recording, perform "Soft Reset":
                // 1. Restart MediaRecorder to get a fresh stream with WebM headers
                // 2. Send 'start' action with same recording_id instead of 'resume'
                if (isReconnect && shouldReconnectRef.current && currentRecordingIdRef.current) {
                    // Stop old recorder if running
                    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                        try {
                            mediaRecorderRef.current.stop()
                        } catch (e) {
                            console.warn('[STT] Failed to stop old recorder during reset:', e)
                        }
                    }

                    // Setup new recorder on existing stream
                    if (streamRef.current) {
                        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                            ? 'audio/webm;codecs=opus'
                            : 'audio/webm'

                        const newMediaRecorder = new MediaRecorder(streamRef.current, { mimeType })

                        newMediaRecorder.ondataavailable = (e) => {
                            if (isPausedRef.current) return
                            if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                                ws.send(e.data)
                            }
                        }

                        mediaRecorderRef.current = newMediaRecorder
                        newMediaRecorder.start(500)
                    }

                    // Send start action with existing ID to re-initialize backend processor
                    ws.send(JSON.stringify({
                        action: 'start',
                        source_lang: currentSourceLangRef.current,
                        target_lang: currentTargetLangRef.current,
                        recording_id: currentRecordingIdRef.current,
                        silence_threshold: currentSilenceThresholdRef.current,
                    }))
                    console.log('[STT] Reset stream and re-sent start action after reconnect')
                }

                resolve(ws)
            }

            ws.onerror = (error) => {
                console.error('WebSocket error:', error)
            }

            ws.onclose = (event) => {
                stopHeartbeat()
                setState(prev => ({ ...prev, isConnected: false }))

                // Attempt reconnection if recording and not deliberately closed
                if (shouldReconnectRef.current && event.code !== 1000) {
                    console.log('[WS onclose] Attempting reconnection, shouldReconnect=true, code=', event.code)
                    setState(prev => {
                        const newAttempts = prev.reconnectAttempts + 1

                        if (newAttempts <= maxReconnectAttempts) {
                            // Exponential backoff capped at 30s
                            const delay = Math.min(30000, reconnectDelay * Math.pow(2, newAttempts - 1))
                            console.log(`WebSocket closed, attempting reconnect ${newAttempts}/${maxReconnectAttempts} in ${delay}ms`)
                            console.log('[WS] Setting connectionStatus to: reconnecting')

                            reconnectTimeoutRef.current = window.setTimeout(async () => {
                                try {
                                    wsRef.current = await connect(true)
                                } catch (err) {
                                    console.error('Reconnection failed:', err)
                                }
                            }, delay)

                            return {
                                ...prev,
                                connectionStatus: 'reconnecting',
                                reconnectAttempts: newAttempts,
                            }
                        } else {
                            // Max attempts reached
                            console.log('[WS] Max attempts reached, setting connectionStatus to: disconnected')
                            return {
                                ...prev,
                                connectionStatus: 'disconnected',
                                error: '连接失败，请检查网络后重试',
                            }
                        }
                    })
                } else {
                    console.log('[WS onclose] No reconnection, shouldReconnect=', shouldReconnectRef.current, 'code=', event.code)
                    console.log('[WS] Setting connectionStatus to: disconnected')
                    setState(prev => ({ ...prev, connectionStatus: 'disconnected' }))
                }
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)

                    // Handle transcript events (Interim vs Final)
                    if (data.type === 'transcript') {
                        if (data.is_final) {
                            // Final result: append to confirmed transcript, clear interim
                            const prefix = transcriptRef.current ? ' ' : ''
                            // Include speaker label if available (diarization)
                            const speakerPrefix = data.speaker ? `[${data.speaker}] ` : ''

                            // 记录当前文本的字符偏移量（用于精确切分）
                            const charOffset = transcriptRef.current.length + prefix.length

                            transcriptRef.current += prefix + speakerPrefix + data.text

                            // 更新后端提供的精确时间戳
                            if (data.start_time !== undefined && segmentStartTimeRef.current === 0) {
                                // 第一个 final，设置 segment 开始时间
                                segmentStartTimeRef.current = data.start_time
                            }
                            if (data.end_time !== undefined) {
                                // 更新 segment 结束时间（累积到最新的结束时间）
                                segmentEndTimeRef.current = data.end_time
                            }

                            // 记录这个 chunk 的时间戳信息（用于精确切分）
                            if (data.start_time !== undefined && data.end_time !== undefined) {
                                timestampedChunksRef.current.push({
                                    text: speakerPrefix + data.text,
                                    start: data.start_time,
                                    end: data.end_time,
                                    charOffset: charOffset
                                })
                            }

                            // 标记等待译文，不立即切分
                            pendingTranslationRef.current = true
                            setState(prev => ({
                                ...prev,
                                transcript: transcriptRef.current,
                                interimTranscript: '' // Clear interim on final
                            }))
                            // 不在这里 checkAndSegment，等译文到达后再切分
                        } else {
                            // Interim result: update interim state (gray text)
                            setState(prev => ({ ...prev, interimTranscript: data.text }))
                        }
                        if (data.chunk_index !== undefined) {
                            lastChunkIndexRef.current = data.chunk_index
                        }
                    } else if (data.type === 'translation') {
                        if (data.is_final) {
                            // Final translation: append to confirmed, clear interim
                            translationRef.current += (translationRef.current ? ' ' : '') + data.text
                            // 译文到达，清除等待标记，检查是否需要切分
                            pendingTranslationRef.current = false
                            setState(prev => ({
                                ...prev,
                                translation: translationRef.current,
                                interimTranslation: ''
                            }))
                            // 译文到达后再检查切分
                            checkAndSegment()
                        } else {
                            // Interim translation (if real-time translation enabled)
                            setState(prev => ({ ...prev, interimTranslation: data.text }))
                        }
                    } else if (data.type === 'error') {
                        console.error('WebSocket error from server:', data.message)
                        setState(prev => ({ ...prev, error: data.message }))
                    } else if (data.type === 'warning') {
                        console.warn('WebSocket warning:', data.message)
                        // Show warning but don't set error state
                    } else if (data.type === 'status') {
                        console.log('WebSocket status:', data.message)
                        // Could be used for UI feedback
                    } else if (data.type === 'audio_saved') {
                        console.log('Audio saved:', data)
                        // Audio was saved successfully
                    } else if (data.type === 'pong') {
                        // Heartbeat response received - connection is alive
                        lastPongTimeRef.current = Date.now()
                        console.log('[Heartbeat] Received pong')
                    } else if (data.type === 'resumed') {
                        // Session resumed successfully after reconnect
                        console.log('Session resumed:', data)
                        lastChunkIndexRef.current = data.chunk_index || 0
                        setState(prev => ({
                            ...prev,
                            isRecording: true,
                            connectionStatus: 'connected',
                        }))
                    } else if (data.type === 'session_expired') {
                        // Session expired, need to restart recording
                        console.warn('Session expired:', data.message)
                        shouldReconnectRef.current = false
                        setState(prev => ({
                            ...prev,
                            error: 'Recording session expired. Please start a new recording.',
                            isRecording: false,
                        }))
                    } else if (data.type === 'auto_stopped') {
                        // Recording auto-stopped due to pause timeout (10 minutes)
                        console.warn('Recording auto-stopped:', data.reason)
                        shouldReconnectRef.current = false
                        setState(prev => ({
                            ...prev,
                            error: '录制已自动结束（暂停超过10分钟）',
                            isRecording: false,
                        }))
                    }
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e)
                }
            }

            wsRef.current = ws
        })
    }, [maxReconnectAttempts, reconnectDelay, startHeartbeat, stopHeartbeat])

    const startRecording = useCallback(async (sourceLang = 'en', targetLang = 'zh', recordingId?: string) => {
        try {
            // Save connection parameters for reconnection
            currentSourceLangRef.current = sourceLang
            currentTargetLangRef.current = targetLang
            currentRecordingIdRef.current = recordingId
            currentSilenceThresholdRef.current = silenceThreshold
            shouldReconnectRef.current = true

            // Reset state
            transcriptRef.current = ''
            translationRef.current = ''

            // 初始化时间戳跟踪
            const now = Date.now()
            recordingStartTimeRef.current = now
            segmentStartTimeRef.current = 0 // 初始化为 0 (因为后端返回的是相对时间)
            segmentEndTimeRef.current = 0
            timestampedChunksRef.current = []  // 清空时间戳 chunks

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

            // Connect WebSocket
            const ws = await connect()

            // Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            })
            streamRef.current = stream

            // Setup VAD (AudioContext)
            const audioContext = new AudioContext()
            const analyser = audioContext.createAnalyser()
            const source = audioContext.createMediaStreamSource(stream)
            source.connect(analyser)
            analyser.fftSize = 256

            audioContextRef.current = audioContext
            analyserRef.current = analyser
            sourceRef.current = source
            maxVolumeRef.current = 0

            // Monitor volume
            vadIntervalRef.current = window.setInterval(() => {
                const dataArray = new Uint8Array(analyser.frequencyBinCount)
                analyser.getByteTimeDomainData(dataArray)

                // Calculate RMS
                let sum = 0
                for (let i = 0; i < dataArray.length; i++) {
                    const x = dataArray[i] - 128
                    sum += x * x
                }
                const rms = Math.sqrt(sum / dataArray.length)

                // Track max volume in current window
                if (rms > maxVolumeRef.current) {
                    maxVolumeRef.current = rms
                }

                // Update currentVolume for UI visualization (normalize to 0-100)
                const normalizedVolume = Math.min(100, Math.round((rms / 60) * 100))
                setState(prev => ({ ...prev, currentVolume: normalizedVolume }))
            }, 50) // Check every 50ms

            // Create MediaRecorder
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm'

            const mediaRecorder = new MediaRecorder(stream, { mimeType })
            mediaRecorderRef.current = mediaRecorder

            // Send audio chunks via WebSocket if volume > threshold
            let chunkCount = 0
            mediaRecorder.ondataavailable = (e) => {
                // Skip sending when paused
                if (isPausedRef.current) {
                    return
                }

                // Use wsRef.current instead of ws to ensure we always use the active connection
                // (ws closure captures the initial socket, which is closed on disconnect)
                const activeWs = wsRef.current

                if (e.data.size > 0 && activeWs && activeWs.readyState === WebSocket.OPEN) {
                    chunkCount++

                    // Check if chunk contained speech (for UI visualization only)
                    const currentMaxVolume = maxVolumeRef.current
                    maxVolumeRef.current = 0 // Reset for next chunk

                    // ALWAYS send all chunks to backend
                    // Previously we dropped silent chunks, but this breaks WebM decoding
                    // because subsequent speech chunks lack the proper WebM header context
                    // The backend can handle the full stream more reliably
                    activeWs.send(e.data)

                    // Log for debugging (first few chunks only)
                    if (chunkCount <= 3) {
                        console.log(`[STT] Sending chunk ${chunkCount}, size=${e.data.size}, volume=${currentMaxVolume.toFixed(1)}`)
                    }
                }
            }

            // Start recording - always use 500ms chunks for real-time display
            // bufferDuration only affects backend processing batch size
            mediaRecorder.start(500)

            // Send start command with recording_id and silence_threshold
            ws.send(JSON.stringify({
                action: 'start',
                source_lang: sourceLang,
                target_lang: targetLang,
                recording_id: recordingId,
                silence_threshold: silenceThreshold,
            }))

            // Start timer
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
        // Stop timer
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }

        // Stop VAD
        if (vadIntervalRef.current) {
            clearInterval(vadIntervalRef.current)
            vadIntervalRef.current = null
        }
        if (sourceRef.current) sourceRef.current.disconnect()
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close()
        }

        // Stop MediaRecorder
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop()
        }

        // Stop media stream
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop())
            streamRef.current = null
        }

        // Disable reconnection before closing
        shouldReconnectRef.current = false

        // Cancel any pending reconnection attempt
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
            reconnectTimeoutRef.current = null
        }

        // Stop heartbeat
        stopHeartbeat()

        // Send stop command
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ action: 'stop' }))

            // Wait a bit for final transcription then close
            await new Promise(resolve => setTimeout(resolve, 2000))
            wsRef.current.close(1000, 'Recording stopped')
        }

        setState(prev => ({ ...prev, isRecording: false, connectionStatus: 'disconnected' }))

        // Merge all historical segments with current buffer
        const finalSegments = [...stateRef.current.segments]
        if (transcriptRef.current.trim()) {
            // 计算最后一个 segment 的时间范围
            const lastSegmentDuration = (Date.now() - recordingStartTimeRef.current) / 1000
            // segmentStartTimeRef.current 已经是后端提供的相对时间（秒）
            const startTime = segmentStartTimeRef.current
            // 如果后端有更新 endTime 则使用，否则使用当前计算的 duration
            const endTime = Math.max(segmentEndTimeRef.current, lastSegmentDuration)

            finalSegments.push({
                text: transcriptRef.current,
                translation: translationRef.current,
                start: startTime,
                end: endTime
            })
        }

        // Combine all segments into full transcript/translation
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
        timestampedChunksRef.current = []  // 清空时间戳 chunks

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

    // Cleanup on unmount
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
