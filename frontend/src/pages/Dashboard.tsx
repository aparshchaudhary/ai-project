import React, { useState } from 'react';
import {
  Globe,
  Camera,
  Calculator,
  Folder,
  Bell,
  History,
  Lock,
  Cpu,
  HardDrive,
  Battery,
  Send,
  Volume2,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { CentralMic } from '../components/CentralMic';
import { VoiceWaveform } from '../components/VoiceWaveform';
import { AssistantState, ConversationTurn, SystemStatus, ReminderItem, AudioDeviceItem, LatencyMetrics } from '../types';

interface DashboardProps {
  assistantState: AssistantState;
  onToggleMic: () => void;
  onStopVoice?: () => void;
  audioLevel: number;
  transcript: string;
  assistantName: string;
  conversationHistory: ConversationTurn[];
  systemStatus: SystemStatus | null;
  reminders: ReminderItem[];
  onExecuteCommand: (text: string) => void;
  onSpeakText: (text: string) => void;
  micMode?: 'desktop' | 'browser';
  onToggleMicMode?: (mode: 'desktop' | 'browser') => void;
  devices?: AudioDeviceItem[];
  selectedDeviceId?: number | null;
  onSelectDevice?: (id: number) => void;
  latencyMetrics?: LatencyMetrics | null;
}

export const Dashboard: React.FC<DashboardProps> = ({
  assistantState,
  onToggleMic,
  onStopVoice,
  audioLevel,
  transcript,
  assistantName,
  conversationHistory,
  systemStatus,
  reminders,
  onExecuteCommand,
  onSpeakText,
  micMode = 'desktop',
  onToggleMicMode,
  devices = [],
  selectedDeviceId = null,
  onSelectDevice,
  latencyMetrics = null,
}) => {
  const [textInput, setTextInput] = useState('');

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim()) return;
    onExecuteCommand(textInput.trim());
    setTextInput('');
  };

  const quickActions = [
    { label: 'Open Browser', command: 'Open Chrome', icon: Globe, color: 'text-blue-400 bg-blue-500/10 hover:border-blue-500/40' },
    { label: 'Take Screenshot', command: 'Take a screenshot', icon: Camera, color: 'text-emerald-400 bg-emerald-500/10 hover:border-emerald-500/40' },
    { label: 'Calculator', command: 'Open Calculator', icon: Calculator, color: 'text-amber-400 bg-amber-500/10 hover:border-amber-500/40' },
    { label: 'File Explorer', command: 'Open my downloads folder', icon: Folder, color: 'text-purple-400 bg-purple-500/10 hover:border-purple-500/40' },
    { label: 'Set Reminder', command: 'Set a reminder for 8 PM to study', icon: Bell, color: 'text-pink-400 bg-pink-500/10 hover:border-pink-500/40' },
    { label: 'Show History', command: 'What commands did I use today?', icon: History, color: 'text-cyan-400 bg-cyan-500/10 hover:border-cyan-500/40' },
    { label: 'Lock Screen', command: 'Lock screen', icon: Lock, color: 'text-rose-400 bg-rose-500/10 hover:border-rose-500/40' },
    { label: 'AI Explain', command: 'Explain machine learning', icon: Sparkles, color: 'text-indigo-400 bg-indigo-500/10 hover:border-indigo-500/40' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Hero: Voice Interaction Hub */}
      <div className="glass-panel rounded-3xl p-6 md:p-8 relative overflow-hidden border border-slate-800 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center">
          <CentralMic
            state={assistantState}
            onToggle={onToggleMic}
            onStopVoice={onStopVoice}
            transcript={transcript}
            assistantName={assistantName}
            micMode={micMode}
            onToggleMicMode={onToggleMicMode}
            audioLevel={audioLevel}
            devices={devices}
            selectedDeviceId={selectedDeviceId}
            onSelectDevice={onSelectDevice}
            latencyMetrics={latencyMetrics}
          />

          <VoiceWaveform
            state={assistantState}
            audioLevel={audioLevel}
            className="my-3"
          />

          {/* Quick Hybrid Text Input Box */}
          <form onSubmit={handleTextSubmit} className="w-full max-w-xl mt-4 flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Or type a command... (e.g. 'Open VS Code', 'What is the date?')"
                className="w-full px-5 py-3 rounded-2xl bg-slate-800/80 border border-slate-700/80 text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition shadow-inner"
              />
            </div>
            <button
              type="submit"
              disabled={!textInput.trim()}
              className="p-3 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:opacity-90 active:scale-95 disabled:opacity-40 disabled:pointer-events-none transition shadow-lg shadow-blue-600/25"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>

      {/* Main Grid: Live Conversation & System / Reminders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Live Conversation Stream (2 cols on large screen) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              Recent Voice & Task Feed
            </h2>
            <span className="text-xs text-slate-400">
              {conversationHistory.length} interactions
            </span>
          </div>

          <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
            {conversationHistory.length === 0 ? (
              <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center text-slate-400">
                <Sparkles className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm font-medium">No commands executed yet.</p>
                <p className="text-xs text-slate-500 mt-1">Tap the microphone above or pick a quick action to start!</p>
              </div>
            ) : (
              conversationHistory.map((turn) => (
                <div
                  key={turn.id}
                  className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2 hover:border-slate-700 transition"
                >
                  {/* User command row */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
                        You
                      </span>
                      <p className="text-sm font-medium text-slate-200">
                        "{turn.user_text}"
                      </p>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {turn.timestamp}
                    </span>
                  </div>

                  {/* Assistant response row */}
                  <div className="flex items-start justify-between gap-3 pl-2 border-l-2 border-blue-500/40">
                    <div>
                      <p className="text-sm text-slate-300">
                        {turn.response_text}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                          {turn.intent}
                        </span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${turn.status === 'success' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-500/15 text-red-300'}`}>
                          {turn.status}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => onSpeakText(turn.response_text)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      title="Replay Voice Audio"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Quick Actions & Hardware Health */}
        <div className="space-y-6">
          {/* Hardware & System Health Meters */}
          {systemStatus && (
            <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
              <h3 className="text-sm font-bold text-slate-100 flex items-center justify-between">
                <span>System Health</span>
                <span className="text-[11px] font-normal text-slate-400 font-mono">{systemStatus.os_name}</span>
              </h3>

              <div className="grid grid-cols-2 gap-3">
                {/* CPU */}
                <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/50">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><Cpu className="w-3.5 h-3.5 text-blue-400" /> CPU</span>
                    <span className="font-semibold text-white">{systemStatus.cpu_percent}%</span>
                  </div>
                  <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-blue-500 h-full rounded-full" style={{ width: `${Math.min(100, systemStatus.cpu_percent)}%` }} />
                  </div>
                </div>

                {/* RAM */}
                <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/50">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><HardDrive className="w-3.5 h-3.5 text-indigo-400" /> RAM</span>
                    <span className="font-semibold text-white">{systemStatus.memory_percent}%</span>
                  </div>
                  <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${Math.min(100, systemStatus.memory_percent)}%` }} />
                  </div>
                </div>

                {/* Disk */}
                <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/50">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><HardDrive className="w-3.5 h-3.5 text-cyan-400" /> Disk</span>
                    <span className="font-semibold text-white">{systemStatus.disk_percent}%</span>
                  </div>
                  <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-cyan-500 h-full rounded-full" style={{ width: `${Math.min(100, systemStatus.disk_percent)}%` }} />
                  </div>
                </div>

                {/* Battery */}
                <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/50">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span className="flex items-center gap-1"><Battery className="w-3.5 h-3.5 text-emerald-400" /> Power</span>
                    <span className="font-semibold text-white">
                      {systemStatus.battery_percent !== null ? `${systemStatus.battery_percent}%` : 'AC Power'}
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${systemStatus.battery_percent || 100}%` }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Quick Actions Panel */}
          <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-slate-100">
              Quick Voice Automation
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {quickActions.map((action, i) => {
                const Icon = action.icon;
                return (
                  <button
                    key={i}
                    onClick={() => onExecuteCommand(action.command)}
                    className={`flex items-center gap-2 p-2.5 rounded-xl border border-slate-800 text-xs font-medium text-slate-300 transition active:scale-95 text-left ${action.color}`}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{action.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Reminders Glance */}
          <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Bell className="w-4 h-4 text-pink-400" />
                Upcoming Reminders
              </h3>
              <span className="text-xs text-slate-400">{reminders.length}</span>
            </div>

            {reminders.length === 0 ? (
              <p className="text-xs text-slate-500">No scheduled reminders.</p>
            ) : (
              <div className="space-y-2">
                {reminders.slice(0, 3).map((r) => (
                  <div key={r.id} className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/50 flex items-center justify-between text-xs">
                    <div className="truncate pr-2">
                      <p className="font-medium text-slate-200 truncate">{r.title}</p>
                      <p className="text-[11px] text-slate-400">
                        {new Date(r.due_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-pink-500/10 text-pink-300 text-[10px] font-bold">
                      Active
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
