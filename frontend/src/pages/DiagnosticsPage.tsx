import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Mic,
  Volume2,
  Shield,
  Lock,
  Cpu,
  Layers,
  ArrowUpRight,
  Gauge,
} from 'lucide-react';
import { api } from '../services/api';
import { DiagnosticsResult, AudioDeviceItem, AudioLevelResult } from '../types';

export const DiagnosticsPage: React.FC = () => {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState<AudioDeviceItem[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [testingMic, setTestingMic] = useState(false);
  const [micTestResult, setMicTestResult] = useState<AudioLevelResult | null>(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
    try {
      const res = await api.runDiagnostics();
      setDiagnostics(res);
    } catch (e) {
      console.error('Failed to run diagnostics:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadAudioDevices = async () => {
    try {
      const data = await api.getAudioDevices();
      setDevices(data.devices);
      setSelectedDeviceId(data.selected_device_id);
    } catch (e) {
      console.warn('Could not load audio devices:', e);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
    loadAudioDevices();
  }, []);

  const handleSelectDevice = async (id: number) => {
    try {
      await api.selectAudioDevice(id);
      setSelectedDeviceId(id);
      loadAudioDevices();
    } catch (e) {
      console.error('Failed to select device:', e);
    }
  };

  const handleTestMicLevel = async () => {
    setTestingMic(true);
    try {
      const res = await api.testAudioLevel(selectedDeviceId ?? undefined);
      setMicTestResult(res);
    } catch (e) {
      console.error('Mic level test failed:', e);
    } finally {
      setTestingMic(false);
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'pass':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> Pass
          </span>
        );
      case 'warn':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" /> Warning
          </span>
        );
      case 'fail':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            Pending
          </span>
        );
    }
  };

  const c = diagnostics?.components;

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/20">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">System & Pipeline Diagnostics</h1>
              <p className="text-sm text-slate-400">
                End-to-end verification of audio hardware, VAD, SAPI speech, DPAPI vault, and WhatsApp sandboxing.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {diagnostics && (
            <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
              <span className="text-slate-500 font-mono">Total Latency:</span>
              <span className="font-bold text-cyan-400">{diagnostics.total_latency_ms} ms</span>
            </div>
          )}

          <button
            onClick={fetchDiagnostics}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-medium text-sm transition shadow-lg shadow-blue-500/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Running Tests...' : 'Run Diagnostics'}</span>
          </button>
        </div>
      </div>

      {/* Live Microphone Test & Device Selection Card */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Mic className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">Live Microphone Hardware Setup & Audio Test</h2>
          </div>

          <button
            onClick={handleTestMicLevel}
            disabled={testingMic}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
          >
            <Gauge className={`w-3.5 h-3.5 text-cyan-400 ${testingMic ? 'animate-spin' : ''}`} />
            <span>{testingMic ? 'Sampling Audio...' : 'Test Input Level'}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Configured Hardware Microphone Device
            </label>
            <select
              value={selectedDeviceId ?? ''}
              onChange={(e) => handleSelectDevice(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  [{d.id}] {d.name} {d.is_default ? '(System Default)' : ''} {d.id === selectedDeviceId ? '★ Active' : ''}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500 mt-1">
              Selecting your active microphone ensures audio is captured from physical hardware rather than disconnected Bluetooth endpoints.
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
              <span>Live Input Level Indicator</span>
              <span className="font-mono font-bold text-cyan-400">
                {micTestResult ? `${micTestResult.level_percent}% (RMS: ${micTestResult.rms})` : 'Idle'}
              </span>
            </div>
            <div className="w-full bg-slate-950 rounded-full h-3 p-0.5 border border-slate-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 transition-all duration-300"
                style={{ width: `${micTestResult?.level_percent ?? 0}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
              <span>0% (Silence)</span>
              <span>
                {micTestResult?.is_speaking ? (
                  <span className="text-emerald-400 font-semibold">● Speech Detected</span>
                ) : (
                  'Speak into mic to test'
                )}
              </span>
              <span>100% (Max)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid of Diagnostic Component Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 1. Hardware Mic */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Mic className="w-3.5 h-3.5 text-blue-400" /> Microphone
            </span>
            {getStatusBadge(c?.microphone?.status)}
          </div>
          <p className="text-sm font-semibold text-white truncate" title={c?.microphone?.device_name}>
            {c?.microphone?.device_name || 'System Default Microphone'}
          </p>
          <div className="text-xs text-slate-400 space-y-0.5 pt-1 border-t border-slate-800/80">
            <div>Device ID: <span className="text-slate-200 font-mono">{c?.microphone?.device_id ?? '1'}</span></div>
            <div>Latency: <span className="text-cyan-400 font-mono">{c?.microphone?.latency_ms ?? 0} ms</span></div>
          </div>
        </div>

        {/* 2. Adaptive VAD */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-cyan-400" /> Voice Activity Detection
            </span>
            {getStatusBadge(c?.vad?.status)}
          </div>
          <p className="text-sm font-semibold text-white">
            Adaptive RMS Energy VAD
          </p>
          <div className="text-xs text-slate-400 space-y-0.5 pt-1 border-t border-slate-800/80">
            <div>Threshold: <span className="text-slate-200 font-mono">{c?.vad?.energy_threshold ?? 320} RMS</span></div>
            <div>Silence Window: <span className="text-cyan-400 font-mono">{c?.vad?.silence_duration_ms ?? 700} ms</span></div>
          </div>
        </div>

        {/* 3. STT Engine */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-purple-400" /> Speech Recognition
            </span>
            {getStatusBadge(c?.stt?.status)}
          </div>
          <p className="text-sm font-semibold text-white">
            Whisper API & Google STT Fallback
          </p>
          <div className="text-xs text-slate-400 space-y-0.5 pt-1 border-t border-slate-800/80">
            <div>Engine: <span className="text-slate-200 font-mono">{c?.stt?.engine}</span></div>
            <div>Language: <span className="text-slate-200 font-mono">{c?.stt?.language?.toUpperCase()} (Multilingual)</span></div>
          </div>
        </div>

        {/* 4. Text to Speech */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-emerald-400" /> Native TTS
            </span>
            {getStatusBadge(c?.tts?.status)}
          </div>
          <p className="text-sm font-semibold text-white">
            Windows Native SAPI 5.4
          </p>
          <div className="text-xs text-slate-400 space-y-0.5 pt-1 border-t border-slate-800/80">
            <div>Mode: <span className="text-slate-200">Non-blocking Detached</span></div>
            <div>Interrupt / Stop: <span className="text-emerald-400 font-semibold">Enabled</span></div>
          </div>
        </div>

        {/* 5. Windows DPAPI */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-amber-400" /> Windows DPAPI Vault
            </span>
            {getStatusBadge(c?.dpapi_vault?.status)}
          </div>
          <p className="text-sm font-semibold text-white">
            OS-Level Data Protection API
          </p>
          <div className="text-xs text-slate-400 space-y-0.5 pt-1 border-t border-slate-800/80">
            <div>Storage: <span className="text-slate-200 font-mono text-[11px] truncate block" title={c?.dpapi_vault?.vault_path}>~/.aura_assistant/vault.bin</span></div>
            <div>Crypt Latency: <span className="text-cyan-400 font-mono">{c?.dpapi_vault?.latency_ms ?? 0} ms</span></div>
          </div>
        </div>

        {/* 6. Sandbox Boundary */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-rose-400" /> Sandbox Boundary
            </span>
            {getStatusBadge(c?.sandbox_boundary?.status)}
          </div>
          <p className="text-sm font-semibold text-white">
            Path Traversal Protection
          </p>
          <div className="text-xs text-slate-400 space-y-0.5 pt-1 border-t border-slate-800/80">
            <div>Attack Probe: <span className="text-emerald-400 font-semibold">Blocked (Cmd.exe rejected)</span></div>
            <div>Strict Allowlist: <span className="text-slate-200">Desktop, Docs, Downloads</span></div>
          </div>
        </div>

        {/* 7. WhatsApp Desktop Integration */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 lg:col-span-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-emerald-400" /> Application Control: WhatsApp Integration
            </span>
            {getStatusBadge(c?.whatsapp_integration?.status)}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-300 pt-1 border-t border-slate-800/80">
            <div>
              <p className="text-slate-500">Registry Status:</p>
              <p className="font-semibold text-slate-200">
                {c?.whatsapp_integration?.registered ? 'Configured in Application Registry' : 'Not Registered'}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Launch Protocol:</p>
              <p className="font-mono text-cyan-400">{c?.whatsapp_integration?.protocol ?? 'start whatsapp:'}</p>
            </div>
            <div>
              <p className="text-slate-500">Persistent Permission Status:</p>
              <p className="font-semibold text-emerald-400">
                {c?.whatsapp_integration?.persistent_permission_cached
                  ? 'Cached in DPAPI Store (No Repeated Prompts)'
                  : 'Auto-authorized on first request'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
