import React, { useState, useEffect } from 'react';
import {
  HelpCircle,
  Search,
  Play,
  AppWindow,
  Globe,
  Folder,
  Cpu,
  Clock,
  CloudSun,
  Music,
  Clipboard,
  Languages,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { HelpCategory } from '../types';

interface HelpPageProps {
  onRunCommand: (command: string) => void;
}

const ICON_MAP: Record<string, any> = {
  AppWindow,
  Globe,
  Folder,
  Cpu,
  Clock,
  CloudSun,
  Music,
  Clipboard,
  Languages,
  Sparkles,
};

export const HelpPage: React.FC<HelpPageProps> = ({ onRunCommand }) => {
  const [categories, setCategories] = useState<HelpCategory[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api.getHelpGuide().then(setCategories).catch(console.error);
  }, []);

  const filteredCategories = categories
    .map((cat) => {
      const filteredCommands = cat.commands.filter(
        (c) =>
          c.text.toLowerCase().includes(search.toLowerCase()) ||
          c.description.toLowerCase().includes(search.toLowerCase())
      );
      return { ...cat, commands: filteredCommands };
    })
    .filter((cat) => cat.commands.length > 0);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
          <HelpCircle className="w-6 h-6 text-blue-400" />
          Interactive Command Guide & Documentation
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Explore all natural language voice commands. Click "Run" on any item to test it live!
        </p>
      </div>

      {/* Search Input */}
      <div className="relative max-w-xl">
        <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search commands (e.g. 'screenshot', 'kholo', 'weather', 'cpu')..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredCategories.map((cat, idx) => {
          const Icon = ICON_MAP[cat.icon] || HelpCircle;
          return (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3"
            >
              <div className="flex items-center gap-2.5 text-white font-bold text-sm border-b border-slate-800 pb-2.5">
                <Icon className="w-4 h-4 text-blue-400" />
                <span>{cat.category}</span>
              </div>

              <div className="space-y-2">
                {cat.commands.map((cmd, cIdx) => (
                  <div
                    key={cIdx}
                    className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/50 flex items-center justify-between gap-3 group hover:border-blue-500/30 transition"
                  >
                    <div>
                      <p className="text-xs font-semibold text-blue-300">
                        "{cmd.text}"
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {cmd.description}
                      </p>
                    </div>

                    <button
                      onClick={() => onRunCommand(cmd.text)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-600/20 text-blue-300 group-hover:bg-blue-600 group-hover:text-white text-[11px] font-semibold transition active:scale-95 flex-shrink-0"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      Run
                    </button>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
