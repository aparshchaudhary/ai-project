import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, Volume2, Shield, Sparkles, Key, Check } from 'lucide-react';
import { api } from '../services/api';
import { AppSettings } from '../types';

interface SettingsPageProps {
  onSettingsSaved?: (newSettings: AppSettings) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ onSettingsSaved }) => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');

  useEffect(() => {
    api.getSettings().then((s) => {
      setSettings(s);
      if (s.openai_api_key) setApiKeyInput(s.openai_api_key);
    });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;

    try {
      const payload: Partial<AppSettings> = {
        ...settings,
        openai_api_key: apiKeyInput,
      };
      const res = await api.updateSettings(payload);
      setSettings(res.settings);
      setSavedSuccess(true);
      if (onSettingsSaved) onSettingsSaved(res.settings);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (e) {
      alert('Error updating settings.');
    }
  };

  if (!settings) return <div className="p-12 text-center text-slate-400">Loading settings...</div>;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
            <SettingsIcon className="w-6 h-6 text-blue-400" />
            Assistant Preferences & Security
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Personalize voice speech, wake word, language, security confirmations, and privacy.
          </p>
        </div>

        {savedSuccess && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold animate-fadeIn">
            <Check className="w-4 h-4" />
            Saved Successfully
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: General & Identity */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-blue-400 flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Assistant Identity
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Assistant Name</label>
              <input
                type="text"
                value={settings.app_name}
                onChange={(e) => setSettings({ ...settings, app_name: e.target.value })}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Wake Word Expression</label>
              <input
                type="text"
                value={settings.wake_word}
                onChange={(e) => setSettings({ ...settings, wake_word: e.target.value })}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Primary Language</label>
              <select
                value={settings.default_language}
                onChange={(e) => setSettings({ ...settings, default_language: e.target.value })}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="en">English (US / Global)</option>
                <option value="hi">Hindi / Hinglish (भारत)</option>
              </select>
            </div>

            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.wake_word_enabled}
                  onChange={(e) => setSettings({ ...settings, wake_word_enabled: e.target.checked })}
                  className="rounded bg-slate-800 border-slate-700 text-blue-500"
                />
                <span>Enable Wake-Word Detection ("Hey Assistant")</span>
              </label>
            </div>
          </div>
        </div>

        {/* Section 2: Voice & Speech Synthesis */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
            <Volume2 className="w-4 h-4" />
            Speech Synthesis (TTS)
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Speech Speed (Words per minute)</span>
                <span className="font-mono text-white">{settings.tts_rate} wpm</span>
              </div>
              <input
                type="range"
                min="100"
                max="260"
                value={settings.tts_rate}
                onChange={(e) => setSettings({ ...settings, tts_rate: Number(e.target.value) })}
                className="w-full accent-emerald-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Speech Volume</span>
                <span className="font-mono text-white">{Math.round(settings.tts_volume * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={settings.tts_volume}
                onChange={(e) => setSettings({ ...settings, tts_volume: Number(e.target.value) })}
                className="w-full accent-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* Section 3: Safety & Permission Controls */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Safety, Permissions & Confirmation Layer
          </h3>

          <div className="space-y-3">
            <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.require_confirmation_high_risk}
                onChange={(e) => setSettings({ ...settings, require_confirmation_high_risk: e.target.checked })}
                className="rounded bg-slate-800 border-slate-700 text-red-500"
              />
              <div className="text-xs">
                <span className="font-semibold text-white block">Require Confirmation for High-Risk Actions</span>
                <span className="text-slate-400">Strictly asks user approval before shutting down, restarting, or deleting files.</span>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.require_confirmation_med_risk}
                onChange={(e) => setSettings({ ...settings, require_confirmation_med_risk: e.target.checked })}
                className="rounded bg-slate-800 border-slate-700 text-amber-500"
              />
              <div className="text-xs">
                <span className="font-semibold text-white block">Require Confirmation for Medium-Risk Actions</span>
                <span className="text-slate-400">Prompts before renaming files, clearing clipboard, or altering configurations.</span>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.clipboard_permission_enabled}
                onChange={(e) => setSettings({ ...settings, clipboard_permission_enabled: e.target.checked })}
                className="rounded bg-slate-800 border-slate-700 text-blue-500"
              />
              <div className="text-xs">
                <span className="font-semibold text-white block">Clipboard Privacy Permission</span>
                <span className="text-slate-400">Allow assistant to read and write clipboard contents.</span>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.demo_mode}
                onChange={(e) => setSettings({ ...settings, demo_mode: e.target.checked })}
                className="rounded bg-slate-800 border-slate-700 text-purple-500"
              />
              <div className="text-xs">
                <span className="font-semibold text-white block">Demo Mode (Presentation / Viva)</span>
                <span className="text-slate-400">Simulates hazardous actions safely during presentations without modifying computer state.</span>
              </div>
            </label>
          </div>
        </div>

        {/* Section 4: Optional Cloud AI Integration */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-purple-400 flex items-center gap-2">
            <Key className="w-4 h-4" />
            Optional Cloud AI / OpenAI Key
          </h3>
          <p className="text-xs text-slate-400">
            The assistant works completely offline with built-in intent parsing. You can optionally add an OpenAI API key for OpenAI Whisper and GPT-4o-mini conversational responses.
          </p>
          <div>
            <label className="text-xs text-slate-400 block mb-1">OpenAI API Key (sk-...)</label>
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="sk-proj-..."
              className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>

        <div className="flex items-center justify-end">
          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-bold shadow-lg shadow-blue-600/30 hover:opacity-95 active:scale-95 transition"
          >
            <Save className="w-4 h-4" />
            Save Preferences
          </button>
        </div>
      </form>
    </div>
  );
};
