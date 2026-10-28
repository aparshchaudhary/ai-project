import React, { useEffect, useRef } from 'react';
import { AssistantState } from '../types';

interface VoiceWaveformProps {
  state: AssistantState;
  audioLevel?: number;
  className?: string;
}

export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({ state, audioLevel = 0, className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let phase = 0;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      const isListening = state === 'listening';
      const isSpeaking = state === 'speaking';
      const isProcessing = state === 'processing' || state === 'executing';

      const barCount = 36;
      const barWidth = Math.max(3, (width / barCount) - 4);
      const centerY = height / 2;

      for (let i = 0; i < barCount; i++) {
        let barHeight = 6;

        if (isListening) {
          const factor = Math.sin((i * 0.3) + phase) * 0.5 + 0.5;
          const levelMultiplier = Math.max(0.2, (audioLevel / 100));
          barHeight = 10 + factor * 48 * levelMultiplier;
        } else if (isSpeaking) {
          const factor = Math.cos((i * 0.4) - phase) * 0.5 + 0.5;
          barHeight = 14 + factor * 38;
        } else if (isProcessing) {
          const factor = Math.sin((i * 0.2) + phase * 2);
          barHeight = 8 + Math.abs(factor) * 22;
        } else {
          // Idle gentle ripple
          const factor = Math.sin((i * 0.25) + phase * 0.5);
          barHeight = 6 + Math.abs(factor) * 8;
        }

        const x = i * (barWidth + 4) + 6;
        const y = centerY - barHeight / 2;

        // Gradient color
        const grad = ctx.createLinearGradient(x, y, x, y + barHeight);
        if (state === 'listening') {
          grad.addColorStop(0, '#38bdf8');
          grad.addColorStop(1, '#818cf8');
        } else if (state === 'speaking') {
          grad.addColorStop(0, '#34d399');
          grad.addColorStop(1, '#06b6d4');
        } else if (state === 'error') {
          grad.addColorStop(0, '#f87171');
          grad.addColorStop(1, '#ef4444');
        } else if (isProcessing) {
          grad.addColorStop(0, '#fbbf24');
          grad.addColorStop(1, '#f59e0b');
        } else {
          grad.addColorStop(0, 'rgba(148, 163, 184, 0.4)');
          grad.addColorStop(1, 'rgba(100, 116, 139, 0.6)');
        }

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 3);
        ctx.fill();
      }

      phase += 0.08;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [state, audioLevel]);

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <canvas
        ref={canvasRef}
        width={340}
        height={70}
        className="max-w-full rounded-xl"
      />
    </div>
  );
};
