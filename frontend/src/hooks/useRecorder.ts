/**
 * useRecorder Hook
 * 录音功能 Hook
 */
import { useState, useRef, useCallback } from 'react'

interface RecorderState {
    isRecording: boolean
    isPaused: boolean
    duration: number
    audioBlob: Blob | null
    audioUrl: string | null
    error: string | null
}

interface UseRecorderReturn extends RecorderState {
    startRecording: () => Promise<void>
    stopRecording: () => Promise<Blob | null>
    pauseRecording: () => void
    resumeRecording: () => void
    resetRecording: () => void
}

export function useRecorder(): UseRecorderReturn {
    const [state, setState] = useState<RecorderState>({
        isRecording: false,
        isPaused: false,
        duration: 0,
        audioBlob: null,
        audioUrl: null,
        error: null,
    })

    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const streamRef = useRef<MediaStream | null>(null)
    const chunksRef = useRef<Blob[]>([])
    const timerRef = useRef<number | null>(null)

    const startRecording = useCallback(async () => {
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            })

            streamRef.current = stream
            chunksRef.current = []

            // Create MediaRecorder
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm'

            const mediaRecorder = new MediaRecorder(stream, { mimeType })
            mediaRecorderRef.current = mediaRecorder

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data)
                }
            }

            mediaRecorder.start(1000) // Collect data every second

            // Start timer
            const startTime = Date.now()
            timerRef.current = window.setInterval(() => {
                setState(prev => ({
                    ...prev,
                    duration: Math.floor((Date.now() - startTime) / 1000)
                }))
            }, 1000)

            setState(prev => ({
                ...prev,
                isRecording: true,
                isPaused: false,
                duration: 0,
                audioBlob: null,
                audioUrl: null,
                error: null,
            }))
        } catch (err) {
            const error = err instanceof Error ? err.message : '无法访问麦克风'
            setState(prev => ({ ...prev, error }))
            throw new Error(error)
        }
    }, [])

    const stopRecording = useCallback(async (): Promise<Blob | null> => {
        return new Promise((resolve) => {
            const mediaRecorder = mediaRecorderRef.current

            if (!mediaRecorder) {
                resolve(null)
                return
            }

            mediaRecorder.onstop = () => {
                // Stop timer
                if (timerRef.current) {
                    clearInterval(timerRef.current)
                    timerRef.current = null
                }

                // Stop all tracks
                if (streamRef.current) {
                    streamRef.current.getTracks().forEach(track => track.stop())
                    streamRef.current = null
                }

                // Create blob
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
                const url = URL.createObjectURL(blob)

                setState(prev => ({
                    ...prev,
                    isRecording: false,
                    isPaused: false,
                    audioBlob: blob,
                    audioUrl: url,
                }))

                resolve(blob)
            }

            mediaRecorder.stop()
        })
    }, [])

    const pauseRecording = useCallback(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
            mediaRecorderRef.current.pause()
            if (timerRef.current) {
                clearInterval(timerRef.current)
            }
            setState(prev => ({ ...prev, isPaused: true }))
        }
    }, [])

    const resumeRecording = useCallback(() => {
        if (mediaRecorderRef.current?.state === 'paused') {
            mediaRecorderRef.current.resume()

            // Resume timer
            const currentDuration = state.duration
            const resumeTime = Date.now()
            timerRef.current = window.setInterval(() => {
                setState(prev => ({
                    ...prev,
                    duration: currentDuration + Math.floor((Date.now() - resumeTime) / 1000)
                }))
            }, 1000)

            setState(prev => ({ ...prev, isPaused: false }))
        }
    }, [state.duration])

    const resetRecording = useCallback(() => {
        // Stop everything
        if (mediaRecorderRef.current) {
            if (mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop()
            }
            mediaRecorderRef.current = null
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop())
            streamRef.current = null
        }

        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }

        // Revoke URL
        if (state.audioUrl) {
            URL.revokeObjectURL(state.audioUrl)
        }

        chunksRef.current = []

        setState({
            isRecording: false,
            isPaused: false,
            duration: 0,
            audioBlob: null,
            audioUrl: null,
            error: null,
        })
    }, [state.audioUrl])

    return {
        ...state,
        startRecording,
        stopRecording,
        pauseRecording,
        resumeRecording,
        resetRecording,
    }
}
