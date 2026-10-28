import React from 'react';
import {
  Mic,
  BrainCircuit,
  ShieldCheck,
  Cpu,
  Volume2,
  Sparkles,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { CentralMic } from '../components/CentralMic';
import { VoiceWaveform } from '../components/VoiceWaveform';
import { AssistantState, CommandExecutionResult } from '../types';

interface AssistantViewProps {
  assistantState: AssistantState;
  onToggleMic: () => void;
  audioLevel: number;
  transcript: string;
  assistantName: string;
  lastResult: CommandExecutionResult | null;
  onSpeakText: (text: string) => void;
  micMode?: 'desktop' | 'browser';
  onToggleMicMode?: (mode: 'desktop' | 'browser') => void;
}

export const AssistantView: React.FC<AssistantViewProps> = ({
  assistantState,
  onToggleMic,
  audioLevel,
  transcript,
  assistantName,
  lastResult,
  onSpeakText,
  micMode = 'desktop',
  onToggleMicMode,
}) => {
  const steps = [
    { num: 1, title: 'Voice Capture', icon: Mic, active: assistantState === 'listening' },
    { num: 2, title: 'STT & NLU', icon: BrainCircuit, active: assistantState === 'processing' },
    { num: 3, title: 'Safety Validation', icon: ShieldCheck, active: assistantState === 'waiting_confirmation' },
    { num: 4, title: 'Task Execution', icon: Cpu, active: assistantState === 'executing' },
    { num: 5, title: 'TTS Response', icon: Volume2, active: assistantState === 'speaking' },
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 flex flex-col items-center">
      {/* Immersive Center Area */}
      <div className="w-full glass-panel rounded-3xl p-8 flex flex-col items-center border border-slate-800 shadow-2xl relative overflow-hidden">
        <div className="text-center mb-2">
          <span className="text-xs font-bold uppercase tracking-widest text-blue-400 bg-blue-500/10 px-3 py-1 rounded-full border border-blue-500/20">
            Dedicated Voice Hub
          </span>
          <h2 className="text-2xl md:text-3xl font-extrabold text-white mt-2">
            Talk to {assistantName}
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-md">
            Speak naturally to control applications, search files, manage schedules, or query information.
          </p>
        </div>

        <CentralMic
          state={assistantState}
          onToggle={onToggleMic}
          transcript={transcript}
          assistantName={assistantName}
          micMode={micMode}
          onToggleMicMode={onToggleMicMode}
        />

        <VoiceWaveform
          state={assistantState}
          audioLevel={audioLevel}
          className="my-4"
        />

        {/* Real-time Pipeline Step Progression */}
        <div className="w-full max-w-2xl mt-4 pt-6 border-t border-slate-800/80">
          <p className="text-xs font-semibold text-slate-400 text-center uppercase tracking-wider mb-4">
            Security & Intent Execution Pipeline
          </p>
          <div className="grid grid-cols-5 gap-2 text-center">
            {steps.map((st) => {
              const Icon = st.icon;
              return (
                <div
                  key={st.num}
                  className={`p-3 rounded-2xl border transition-all ${st.active ? 'bg-blue-600/20 border-blue-500 text-blue-300 ring-2 ring-blue-500/30' : 'bg-slate-800/40 border-slate-800 text-slate-500'}`}
                >
                  <Icon className={`w-5 h-5 mx-auto mb-1 ${st.active ? 'text-blue-400 animate-pulse' : 'text-slate-500'}`} />
                  <p className="text-[11px] font-semibold truncate">{st.title}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Structured Intent Details for Latest Command */}
      {lastResult && (
        <div className="w-full p-6 rounded-3xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Structured AI Intent Output
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Latency: {lastResult.execution_time_ms.toFixed(1)} ms
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <span className="text-slate-400 block mb-1">Detected Intent:</span>
              <span className="font-bold text-blue-300 text-sm">{lastResult.intent}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <span className="text-slate-400 block mb-1">Risk Level:</span>
              <span className={`font-bold uppercase text-sm ${lastResult.risk_level === 'high' ? 'text-red-400' : (lastResult.risk_level === 'medium' ? 'text-amber-400' : 'text-emerald-400')}`}>
                {lastResult.risk_level}
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <span className="text-slate-400 block mb-1">Status:</span>
              <span className="font-bold text-emerald-300 text-sm uppercase">{lastResult.status}</span>
            </div>
          </div>

          {/* Response Box */}
          <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-blue-400 uppercase tracking-wide block">
                Assistant Response
              </span>
              <p className="text-sm font-medium text-slate-200 mt-0.5">
                "{lastResult.response_text}"
              </p>
            </div>
            <button
              onClick={() => onSpeakText(lastResult.response_text)}
              className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white transition shadow-md"
              title="Speak Again"
            >
              <Volume2 className="w-4 h-4" />
            </button>
          </div>

          {/* Entities JSON representation */}
          {Object.keys(lastResult.entities).length > 0 && (
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs">
              <span className="text-slate-500 font-bold block mb-1">Extracted Entities:</span>
              <pre className="text-slate-300 overflow-x-auto">
                {JSON.stringify(lastResult.entities, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
