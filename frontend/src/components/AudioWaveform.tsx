/**
 * AudioWaveform Component
 * Real-time audio waveform visualization using Canvas
 * Used during recording to show live audio levels
 */
import { useRef, useEffect, useCallback } from 'react'

interface AudioWaveformProps {
    /** Whether recording is active */
    isRecording: boolean
    /** Audio analyser node from AudioContext */
    analyser: AnalyserNode | null
    /** Width of the canvas */
    width?: number
    /** Height of the canvas */
    height?: number
    /** Waveform color (CSS color) */
    color?: string
    /** Background color (CSS color) */
    backgroundColor?: string
    /** Number of bars to display */
    barCount?: number
    /** Gap between bars in pixels */
    barGap?: number
}

export default function AudioWaveform({
    isRecording,
    analyser,
    width = 300,
    height = 60,
    color = '#a855f7', // brand-500
    backgroundColor = 'transparent',
    barCount = 32,
    barGap = 2,
}: AudioWaveformProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animationRef = useRef<number | null>(null)

    const draw = useCallback(() => {
        const canvas = canvasRef.current
        if (!canvas || !analyser) return

        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const bufferLength = analyser.frequencyBinCount
        const dataArray = new Uint8Array(bufferLength)
        analyser.getByteFrequencyData(dataArray)

        // Clear canvas
        ctx.fillStyle = backgroundColor
        ctx.fillRect(0, 0, width, height)

        // Calculate bar dimensions
        const barWidth = (width - (barCount - 1) * barGap) / barCount
        const samplesPerBar = Math.floor(bufferLength / barCount)

        // Draw bars
        for (let i = 0; i < barCount; i++) {
            // Average the samples for this bar
            let sum = 0
            for (let j = 0; j < samplesPerBar; j++) {
                sum += dataArray[i * samplesPerBar + j]
            }
            const average = sum / samplesPerBar

            // Calculate bar height (normalized to 0-1)
            const normalizedHeight = average / 255
            const barHeight = Math.max(2, normalizedHeight * height * 0.9)

            // Calculate x position
            const x = i * (barWidth + barGap)

            // Draw bar centered vertically
            const y = (height - barHeight) / 2

            // Gradient effect - more intense at peaks
            const alpha = 0.5 + normalizedHeight * 0.5
            ctx.fillStyle = color.replace(')', `, ${alpha})`).replace('rgb', 'rgba')

            ctx.beginPath()
            ctx.roundRect(x, y, barWidth, barHeight, 2)
            ctx.fill()
        }

        // Continue animation
        if (isRecording) {
            animationRef.current = requestAnimationFrame(draw)
        }
    }, [analyser, isRecording, width, height, color, backgroundColor, barCount, barGap])

    useEffect(() => {
        if (isRecording && analyser) {
            draw()
        }

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current)
            }
        }
    }, [isRecording, analyser, draw])

    // Draw idle state when not recording
    useEffect(() => {
        if (!isRecording) {
            const canvas = canvasRef.current
            if (!canvas) return

            const ctx = canvas.getContext('2d')
            if (!ctx) return

            ctx.fillStyle = backgroundColor
            ctx.fillRect(0, 0, width, height)

            // Draw idle bars (flat line)
            const barWidth = (width - (barCount - 1) * barGap) / barCount
            ctx.fillStyle = color.replace(')', ', 0.3)').replace('rgb', 'rgba')

            for (let i = 0; i < barCount; i++) {
                const x = i * (barWidth + barGap)
                const barHeight = 4
                const y = (height - barHeight) / 2

                ctx.beginPath()
                ctx.roundRect(x, y, barWidth, barHeight, 2)
                ctx.fill()
            }
        }
    }, [isRecording, width, height, color, backgroundColor, barCount, barGap])

    return (
        <canvas
            ref={canvasRef}
            width={width}
            height={height}
            className="rounded-lg"
            style={{ backgroundColor }}
        />
    )
}
