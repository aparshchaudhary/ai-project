import React from 'react';
import { PlayCircle, Sparkles } from 'lucide-react';

interface DemoBarProps {
  onRunSample: (command: string) => void;
}

const SAMPLE_COMMANDS = [
  { text: 'Open Chrome', category: 'App' },
  { text: 'Take a screenshot', category: 'Action' },
  { text: 'Show system information', category: 'System' },
  { text: "What's the weather today?", category: 'Info' },
  { text: 'Search Google for machine learning', category: 'Web' },
  { text: 'Create a folder called College Projects', category: 'File' },
  { text: 'Set a reminder for 8 PM to study', category: 'Reminder' },
  { text: 'Chrome kholo', category: 'Hindi' },
  { text: 'Explain machine learning', category: 'AI' },
  { text: 'Turn off the computer', category: 'Safety' },
];

export const DemoBar: React.FC<DemoBarProps> = ({ onRunSample }) => {
  return (
    <div className="w-full bg-slate-900/80 dark:bg-slate-900/90 border-y border-slate-800/80 px-4 py-2.5 backdrop-blur-md">
      <div className="max-w-7xl mx-auto flex items-center gap-3 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1.5 flex-shrink-0 text-xs font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-md border border-blue-500/20">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Demo Showcase</span>
        </div>

        <div className="flex items-center gap-2 flex-nowrap">
          {SAMPLE_COMMANDS.map((cmd, idx) => (
            <button
              key={idx}
              onClick={() => onRunSample(cmd.text)}
              className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1 bg-slate-800/70 hover:bg-blue-600/30 text-slate-300 hover:text-blue-300 border border-slate-700/60 hover:border-blue-500/40 rounded-lg text-xs font-medium transition active:scale-95 group"
            >
              <PlayCircle className="w-3 h-3 text-slate-400 group-hover:text-blue-400 transition" />
              <span>"{cmd.text}"</span>
              <span className="text-[10px] text-slate-400 bg-slate-700/50 px-1 rounded ml-0.5">
                {cmd.category}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
