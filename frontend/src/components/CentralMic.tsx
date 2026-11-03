import React from 'react';
import {
  Mic,
  MicOff,
  Loader2,
  Volume2,
  ShieldAlert,
  Sparkles,
  Square,
  Clock,
  Radio,
  Activity,
  AlertCircle,
  Repeat,
  HandMetal,
} from 'lucide-react';
import { AssistantState, AudioDeviceItem, LatencyMetrics } from '../types';
import { ListeningMode } from '../hooks/useVoiceRecognition';
import { VoiceWaveform } from './VoiceWaveform';

interface CentralMicProps {
  state: AssistantState;
  onToggle: () => void;
  onStopVoice?: () => void;
  transcript?: string;
  assistantName?: string;
  audioLevel?: number;
  devices?: AudioDeviceItem[];
  selectedDeviceId?: number | null;
  onSelectDevice?: (id: number) => void;
  latencyMetrics?: LatencyMetrics | null;
  listeningMode?: ListeningMode;
  onToggleListeningMode?: (mode: ListeningMode) => void;
  listeningDuration?: number;
  connectionStatus?: 'idle' | 'connecting' | 'connected' | 'listening' | 'error';
  lastRecognizedCommand?: string;
  errorMessage?: string | null;
  micMode?: 'desktop' | 'browser';
  onToggleMicMode?: (mode: 'desktop' | 'browser') => void;
}

export const CentralMic: React.FC<CentralMicProps> = ({
  state,
  onToggle,
  onStopVoice,
  transcript,
  assistantName = 'Aura',
  audioLevel = 0,
  devices = [],
  selectedDeviceId = null,
  onSelectDevice,
  latencyMetrics = null,
  listeningMode = 'push_to_talk',
  onToggleListeningMode,
  listeningDuration = 0,
  connectionStatus = 'idle',
  lastRecognizedCommand = '',
  errorMessage = null,
  micMode = 'browser',
  onToggleMicMode,
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
        return listeningMode === 'continuous'
          ? 'Continuous Listening Active — speak naturally...'
          : 'Listening... (Speak your command)';
      case 'processing':
        return 'Processing command & verifying...';
      case 'executing':
        return 'Executing task safely...';
      case 'speaking':
        return `${assistantName} is speaking... (Click Stop or press Esc)`;
      case 'waiting_confirmation':
        return 'Safety check: Confirmation required';
      case 'error':
        return errorMessage || 'Voice input notice. Click to retry';
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

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col items-center justify-center my-4 w-full max-w-xl mx-auto">
      {/* Interaction Mode Selector Pill (Push-to-Talk vs Continuous Listening) */}
      <div className="mb-4 inline-flex items-center gap-1.5 p-1 bg-slate-900/90 border border-slate-800 rounded-full text-xs shadow-inner">
        <button
          type="button"
          onClick={() => onToggleListeningMode && onToggleListeningMode('push_to_talk')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-semibold transition ${
            listeningMode === 'push_to_talk'
              ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <HandMetal className="w-3.5 h-3.5" />
          <span>Push-to-Talk</span>
        </button>
        <button
          type="button"
          onClick={() => onToggleListeningMode && onToggleListeningMode('continuous')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-semibold transition ${
            listeningMode === 'continuous'
              ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Repeat className="w-3.5 h-3.5" />
          <span>Continuous Listening</span>
        </button>
      </div>

      {/* Connection & Live Hardware Status Indicator */}
      <div className="mb-3 flex items-center justify-center gap-3 text-xs">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-slate-300">
          <span
            className={`w-2 h-2 rounded-full ${
              state === 'listening'
                ? 'bg-emerald-400 animate-ping'
                : state === 'speaking'
                ? 'bg-cyan-400'
                : 'bg-slate-500'
            }`}
          />
          <Radio className="w-3 h-3 text-cyan-400" />
          <span className="font-mono">
            {state === 'listening'
              ? 'Mic Stream: ACTIVE'
              : state === 'speaking'
              ? 'Audio Output: ACTIVE'
              : 'Mic Stream: STANDBY'}
          </span>
        </span>

        {/* Live Listening Stopwatch Timer */}
        {state === 'listening' && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 font-mono text-xs">
            <Clock className="w-3 h-3 text-cyan-400 animate-spin" />
            <span>{formatDuration(listeningDuration)}</span>
          </span>
        )}
      </div>

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
          type="button"
          onClick={state === 'speaking' && onStopVoice ? onStopVoice : onToggle}
          className={`group relative z-10 w-28 h-28 rounded-full bg-gradient-to-tr ${getStatusColor()} flex items-center justify-center shadow-xl ring-4 transition-all duration-300 hover:scale-105 active:scale-95`}
          title={
            state === 'speaking'
              ? 'Click to stop speaking'
              : state === 'listening'
              ? 'Click to stop listening'
              : 'Click to start voice input'
          }
        >
          {state === 'speaking' ? (
            <Square className="w-10 h-10 text-white fill-white animate-pulse" />
          ) : (
            renderIcon()
          )}
        </button>
      </div>

      {/* Audio Input Level Meter Bar */}
      {state === 'listening' && (
        <div className="mt-4 w-64 bg-slate-900/80 border border-slate-800 rounded-full p-1 shadow-inner">
          <div className="flex items-center gap-2 px-2 text-[10px] text-slate-400 font-mono mb-0.5 justify-between">
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-cyan-400" /> Input Level
            </span>
            <span className="text-cyan-300">{audioLevel}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 transition-all duration-75"
              style={{ width: `${Math.max(5, audioLevel)}%` }}
            />
          </div>
        </div>
      )}

      {/* Real-time Waveform Canvas */}
      <div className="w-full max-w-sm mt-3 px-4">
        <VoiceWaveform state={state} audioLevel={audioLevel} className="w-full h-12" />
      </div>

      {/* Dynamic Status & Prompts */}
      <div className="mt-2 text-center px-4">
        <div className="flex items-center justify-center gap-2">
          <span className="text-[11px] font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            {state}
          </span>

          {state === 'listening' && (
            <button
              type="button"
              onClick={onToggle}
              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-rose-900/60 text-rose-300 border border-rose-700 hover:bg-rose-800 transition"
            >
              <Square className="w-3 h-3 fill-rose-300" /> Stop Listening
            </button>
          )}

          {state === 'speaking' && onStopVoice && (
            <button
              type="button"
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

        {/* Live Partial Speech Transcript */}
        {transcript && (
          <div className="mt-2.5 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full inline-flex items-center gap-2 max-w-lg">
            <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0" />
            <span className="text-sm font-medium text-blue-300 truncate">
              "{transcript}"
            </span>
          </div>
        )}

        {/* Last Recognized Command */}
        {lastRecognizedCommand && !transcript && (
          <div className="mt-2 text-xs text-slate-400 font-mono">
            Last heard: <span className="text-slate-200">"{lastRecognizedCommand}"</span>
          </div>
        )}

        {/* Error notification banner */}
        {errorMessage && (
          <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 bg-red-950/80 border border-red-800 rounded-lg text-xs text-red-300">
            <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Latency Breakdown */}
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
