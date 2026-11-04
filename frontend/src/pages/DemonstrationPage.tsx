import React, { useState } from 'react';
import {
  Sparkles,
  Play,
  Terminal,
  Activity,
  Award,
  Layers,
  Cpu,
  CheckCircle2,
  Volume2,
  FileCode,
  ExternalLink,
  Laptop,
} from 'lucide-react';
import { CentralMic } from '../components/CentralMic';
import { DesktopActivityPanel, DesktopActivityItem } from '../components/DesktopActivityPanel';
import { AiAgentActivityPanel } from '../components/AiAgentActivityPanel';
import { AssistantState, CommandExecutionResult, AgentTaskPlan, ContactItem } from '../types';
import { ListeningMode } from '../hooks/useVoiceRecognition';

interface DemonstrationPageProps {
  assistantState: AssistantState;
  onToggleMic: () => void;
  onStopVoice?: () => void;
  transcript: string;
  lastResult: CommandExecutionResult | null;
  onExecuteCommand: (text: string) => void;
  audioLevel?: number;
  listeningMode: ListeningMode;
  onToggleListeningMode: (mode: ListeningMode) => void;
  listeningDuration?: number;
  connectionStatus?: 'idle' | 'connecting' | 'connected' | 'listening' | 'error';
  lastRecognizedCommand?: string;
  errorMessage?: string | null;
  desktopActivities: DesktopActivityItem[];
  onClearActivities?: () => void;
  activePlan?: AgentTaskPlan | null;
  onConfirmPlan?: (planId: string, confirmationId?: string) => void;
  onCancelPlan?: (planId: string) => void;
  onRetryTask?: (taskId: string) => void;
  onSelectContact?: (contact: ContactItem) => void;
}

export const DemonstrationPage: React.FC<DemonstrationPageProps> = ({
  assistantState,
  onToggleMic,
  onStopVoice,
  transcript,
  lastResult,
  onExecuteCommand,
  audioLevel = 0,
  listeningMode,
  onToggleListeningMode,
  listeningDuration = 0,
  connectionStatus = 'idle',
  lastRecognizedCommand = '',
  errorMessage = null,
  desktopActivities,
  onClearActivities,
  activePlan = null,
  onConfirmPlan,
  onCancelPlan,
  onRetryTask,
  onSelectContact,
}) => {
  const [selectedDemoCommand, setSelectedDemoCommand] = useState<string | null>(null);

  const sampleCommands = [
    { label: 'Open Chrome', command: 'Open Chrome', icon: '🌐', category: 'Browser' },
    { label: 'Open WhatsApp', command: 'Open WhatsApp', icon: '💬', category: 'Chat' },
    { label: 'Open Calculator', command: 'Open Calculator', icon: '🧮', category: 'Utility' },
    { label: 'Open Notepad', command: 'Open Notepad', icon: '📝', category: 'Editor' },
    { label: 'Open VS Code', command: 'Open VS Code', icon: '💻', category: 'Development' },
    { label: 'Take a screenshot', command: 'Take a screenshot', icon: '📸', category: 'System' },
    { label: 'Search AI on Google', command: 'Search Google for Artificial Intelligence', icon: '🔍', category: 'Web' },
    { label: 'Show system info', command: 'Show system information', icon: '⚙️', category: 'Diagnostics' },
  ];

  const handleRunSample = (cmd: string) => {
    setSelectedDemoCommand(cmd);
    onExecuteCommand(cmd);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Presentation Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900/60 via-indigo-900/50 to-slate-900/80 border border-blue-700/40 p-6 shadow-2xl backdrop-blur-md">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 text-xs font-semibold uppercase tracking-wider mb-2">
              <Award className="w-3.5 h-3.5" /> Academic Project Demonstration Mode
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              AI Desktop Voice Assistant V2
            </h1>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              End-to-End Real Voice Execution: Voice Input → Natural Language Intent Engine → OS Process Execution → Window Verification → Spoken Confirmation.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700 text-xs font-mono text-cyan-300">
              <Laptop className="w-4 h-4 text-cyan-400" />
              <span>Real Laptop OS Mode</span>
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700 text-xs font-mono text-emerald-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Live Window Hooks</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Interactive Mic Section */}
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800 p-6 shadow-xl backdrop-blur-md flex flex-col items-center">
        <CentralMic
          state={assistantState}
          onToggle={onToggleMic}
          onStopVoice={onStopVoice}
          transcript={transcript}
          assistantName="Aura"
          audioLevel={audioLevel}
          listeningMode={listeningMode}
          onToggleListeningMode={onToggleListeningMode}
          listeningDuration={listeningDuration}
          connectionStatus={connectionStatus}
          lastRecognizedCommand={lastRecognizedCommand}
          errorMessage={errorMessage}
        />
      </div>

      {/* 8 Presentation Sample Commands Chips */}
      <div className="rounded-2xl bg-slate-900/70 border border-slate-800 p-5 shadow-xl backdrop-blur-md">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-cyan-400" />
            <h3 className="font-semibold text-slate-100 text-sm">
              One-Click Demonstration Triggers
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            Click any command or speak it into the microphone
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {sampleCommands.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleRunSample(item.command)}
              className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                selectedDemoCommand === item.command
                  ? 'bg-blue-600/20 border-cyan-500 shadow-md ring-1 ring-cyan-500/50'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="text-lg">{item.icon}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                  {item.category}
                </span>
              </div>
              <div className="font-semibold text-xs text-slate-200 truncate">
                {item.label}
              </div>
              <div className="text-[11px] text-cyan-400/90 font-mono mt-1 flex items-center gap-1">
                <Play className="w-2.5 h-2.5" /> Execute
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* AI Agent Multi-Command DAG Execution Activity */}
      <AiAgentActivityPanel
        plan={activePlan}
        onConfirmPlan={onConfirmPlan}
        onCancelPlan={onCancelPlan}
        onRetryTask={onRetryTask}
        onSelectContact={onSelectContact}
        onRunSampleCommand={onExecuteCommand}
      />

      {/* Two-Column Execution Lifecycle Inspection Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Intent Classification & Execution Result */}
        <div className="space-y-6">
          {/* Intent Classification Card */}
          <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl backdrop-blur-md">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800 mb-4">
              <Terminal className="w-4 h-4 text-purple-400" />
              <h3 className="font-semibold text-slate-100 text-sm">
                Intent Engine & NLP Pipeline
              </h3>
            </div>

            {lastResult ? (
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                  <div className="text-xs text-slate-400 mb-1">Recognized Command</div>
                  <div className="text-sm font-semibold text-cyan-300 font-mono">
                    "{lastResult.entities?.application ? `Open ${lastResult.entities.application}` : lastResult.intent}"
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                    <div className="text-xs text-slate-400 mb-0.5">Classified Intent</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono uppercase">
                      {lastResult.intent}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                    <div className="text-xs text-slate-400 mb-0.5">Risk Level</div>
                    <div className="text-xs font-bold text-cyan-400 font-mono uppercase">
                      {lastResult.risk_level || 'Safe'}
                    </div>
                  </div>
                </div>

                {lastResult.entities && Object.keys(lastResult.entities).length > 0 && (
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
                    <div className="text-slate-400 mb-1">Extracted Entities</div>
                    <pre className="text-slate-300 font-mono text-[11px] overflow-x-auto">
                      {JSON.stringify(lastResult.entities, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 text-xs">
                Run or speak a command to view real-time intent parsing.
              </div>
            )}
          </div>

          {/* Voice Response Confirmation Card */}
          {lastResult && (
            <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl backdrop-blur-md">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-800 mb-3">
                <Volume2 className="w-4 h-4 text-emerald-400" />
                <h3 className="font-semibold text-slate-100 text-sm">
                  Verified Voice Feedback
                </h3>
              </div>
              <p className="text-sm font-medium text-emerald-300 bg-emerald-950/40 border border-emerald-800/40 p-3.5 rounded-xl">
                "{lastResult.response_text}"
              </p>
              {lastResult.execution_time_ms !== undefined && (
                <div className="text-right text-[11px] text-slate-500 font-mono mt-2">
                  Total pipeline latency: {Math.round(lastResult.execution_time_ms)}ms
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Live Desktop Activity Panel */}
        <div>
          <DesktopActivityPanel
            activities={desktopActivities}
            onClearActivities={onClearActivities}
            className="h-full"
          />
        </div>
      </div>
    </div>
  );
};
