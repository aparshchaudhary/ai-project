import React from 'react';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';

interface ConfirmationModalProps {
  isOpen: boolean;
  prompt: string;
  intent: string;
  riskLevel: 'medium' | 'high';
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  prompt,
  intent,
  riskLevel,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  const isHighRisk = riskLevel === 'high';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden p-6 text-white">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-xl flex-shrink-0 ${isHighRisk ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'}`}>
            <AlertTriangle className="w-7 h-7" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className={`text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${isHighRisk ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'}`}>
                {riskLevel} Risk Action
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {intent}
              </span>
            </div>
            <h3 className="text-lg font-bold text-white mt-1">
              Safety Confirmation Required
            </h3>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Prompt content */}
        <div className="mt-4 p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
          <p className="text-slate-200 text-sm md:text-base font-medium">
            {prompt}
          </p>
        </div>

        <p className="text-xs text-slate-400 mt-3">
          This system requires explicit user permission before executing potentially destructive or system-level computer tasks.
        </p>

        {/* Action buttons */}
        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2.5 rounded-xl text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            Cancel / Reject
          </button>
          <button
            onClick={onConfirm}
            className={`px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-lg flex items-center gap-2 transition ${isHighRisk ? 'bg-red-600 hover:bg-red-500 shadow-red-600/30' : 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/30'}`}
          >
            <ShieldCheck className="w-4 h-4" />
            Confirm & Execute
          </button>
        </div>
      </div>
    </div>
  );
};
