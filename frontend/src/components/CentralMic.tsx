import React from 'react';
import {
  Mic,
  MicOff,
  Loader2,
  Volume2,
  ShieldAlert,
  Sparkles,
  Cpu,
  Globe,
  Square,
  Clock,
  Settings2,
} from 'lucide-react';
import { AssistantState, AudioDeviceItem, LatencyMetrics } from '../types';

interface CentralMicProps {
  state: AssistantState;
  onToggle: () => void;
  onStopVoice?: () => void;
  transcript?: string;
  assistantName?: string;
  micMode?: 'desktop' | 'browser';
  onToggleMicMode?: (mode: 'desktop' | 'browser') => void;
  audioLevel?: number;
  devices?: AudioDeviceItem[];
  selectedDeviceId?: number | null;
  onSelectDevice?: (id: number) => void;
  latencyMetrics?: LatencyMetrics | null;
}

export const CentralMic: React.FC<CentralMicProps> = ({
  state,
  onToggle,
  onStopVoice,
  transcript,
  assistantName = 'Aura',
  micMode = 'desktop',
  onToggleMicMode,
  audioLevel = 0,
  devices = [],
  selectedDeviceId = null,
  onSelectDevice,
  latencyMetrics = null,
}) => {
  const getStatusColor = () => {
    switch (state) {
      case 'listening':
        return 'from-cyan-500 to-blue-600 shadow-cyan-500/50 ring-cyan-400';
      case 'processing':
        return 'from-amber-500 to-orange-600 shadow-amber-500/50 ring-amber-400';
      case 'executing':
        return 'from-purple-500 to-indigo-600 shadow-purple-500/50 ring-purple-400';
      case 'speaking':
        return 'from-emerald-500 to-teal-600 shadow-emerald-500/50 ring-emerald-400';
      case 'waiting_confirmation':
        return 'from-rose-500 to-red-600 shadow-rose-500/50 ring-rose-400';
      case 'error':
        return 'from-red-500 to-rose-700 shadow-red-500/50 ring-red-400';
      default:
        return 'from-blue-600 to-indigo-700 shadow-blue-500/30 ring-blue-500/40';
    }
  };

  const getStatusText = () => {
    switch (state) {
      case 'listening':
        return micMode === 'desktop'
          ? 'Listening via Hardware Mic... (Adaptive VAD active)'
          : 'Listening via Browser Speech...';
      case 'processing':
        return 'Analyzing intent & entities...';
      case 'executing':
        return 'Executing task safely...';
      case 'speaking':
        return `${assistantName} is speaking... (Click Stop or press Esc)`;
      case 'waiting_confirmation':
        return 'Safety check: Confirmation required';
      case 'error':
        return 'No speech detected or mic timeout. Tap to retry';
      default:
        return `Click the microphone or press Space to speak`;
    }
  };

  const renderIcon = () => {
    switch (state) {
      case 'listening':
        return <Mic className="w-12 h-12 text-white animate-pulse" />;
      case 'processing':
      case 'executing':
        return <Loader2 className="w-12 h-12 text-white animate-spin" />;
      case 'speaking':
        return <Volume2 className="w-12 h-12 text-white animate-bounce" />;
      case 'waiting_confirmation':
        return <ShieldAlert className="w-12 h-12 text-white" />;
      case 'error':
        return <MicOff className="w-12 h-12 text-white" />;
      default:
        return <Mic className="w-12 h-12 text-white group-hover:scale-110 transition-transform duration-200" />;
    }
  };

  return (
    <div className="flex flex-col items-center justify-center my-4">
      {/* Mic Mode Selector Pill */}
      {onToggleMicMode && (
        <div className="mb-3 inline-flex items-center gap-1.5 p-1 bg-slate-900/90 border border-slate-800 rounded-full text-xs shadow-inner">
          <button
            onClick={() => onToggleMicMode('desktop')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-semibold transition ${micMode === 'desktop' ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md' : 'text-slate-400 hover:text-white'}`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Hardware Desktop Mic (Recommended)</span>
          </button>
          <button
            onClick={() => onToggleMicMode('browser')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-semibold transition ${micMode === 'browser' ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md' : 'text-slate-400 hover:text-white'}`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Browser Web Speech</span>
          </button>
        </div>
      )}

      {/* Microphone Hardware Device Selector Dropdown */}
      {micMode === 'desktop' && devices.length > 0 && onSelectDevice && (
        <div className="mb-4 flex items-center gap-2 max-w-md w-full px-4">
          <Settings2 className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <select
            value={selectedDeviceId ?? ''}
            onChange={(e) => onSelectDevice(Number(e.target.value))}
            className="flex-1 bg-slate-900/80 border border-slate-800 text-slate-300 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-cyan-500 truncate"
            title="Select audio hardware input device"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} {d.is_default ? '(Default)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Central Animated Mic Button */}
      <div className="relative flex items-center justify-center">
        {state === 'listening' && (
          <>
            <div className="absolute w-36 h-36 rounded-full bg-cyan-500/20 animate-ping" />
            <div className="absolute w-44 h-44 rounded-full bg-blue-500/15 animate-pulse" />
          </>
        )}

        {state === 'speaking' && (
          <div className="absolute w-40 h-40 rounded-full bg-emerald-500/20 animate-pulse" />
        )}

        <button
          onClick={state === 'speaking' && onStopVoice ? onStopVoice : onToggle}
          className={`group relative z-10 w-28 h-28 rounded-full bg-gradient-to-tr ${getStatusColor()} flex items-center justify-center shadow-xl ring-4 transition-all duration-300 hover:scale-105 active:scale-95`}
          title={state === 'speaking' ? 'Click to stop speaking' : (state === 'listening' ? 'Listening...' : 'Click to start voice input')}
        >
          {state === 'speaking' ? (
            <Square className="w-10 h-10 text-white fill-white animate-pulse" />
          ) : (
            renderIcon()
          )}
        </button>
      </div>

      {/* Dynamic Status & Prompt */}
      <div className="mt-4 text-center px-4">
        <div className="flex items-center justify-center gap-2">
          <span className="text-[11px] font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            {state}
          </span>

          {state === 'speaking' && onStopVoice && (
            <button
              onClick={onStopVoice}
              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-900/60 text-rose-300 border border-rose-700 hover:bg-rose-800 transition"
            >
              <Square className="w-3 h-3 fill-rose-300" /> Stop Speaking (Esc)
            </button>
          )}
        </div>

        <h3 className="text-lg md:text-xl font-medium text-slate-100 mt-2">
          {getStatusText()}
        </h3>

        {transcript && (
          <div className="mt-2.5 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full inline-flex items-center gap-2 max-w-lg">
            <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0" />
            <span className="text-sm font-medium text-blue-300 truncate">
              "{transcript}"
            </span>
          </div>
        )}

        {/* Real-time Measured Latency Breakdown */}
        {latencyMetrics && (
          <div className="mt-3 inline-flex items-center gap-3 px-3 py-1 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-cyan-400" />
              <span>VAD: <strong className="text-cyan-300">{latencyMetrics.vad_capture_ms ?? 0}ms</strong></span>
            </span>
            <span className="text-slate-600">|</span>
            <span>STT: <strong className="text-purple-300">{latencyMetrics.stt_transcription_ms ?? 0}ms</strong></span>
            <span className="text-slate-600">|</span>
            <span>Total: <strong className="text-emerald-400">{latencyMetrics.total_speech_ms ?? 0}ms</strong></span>
          </div>
        )}
      </div>
    </div>
  );
};
