import React from 'react';
import { AlertTriangle, ShieldCheck, X, Send, User, MessageCircle } from 'lucide-react';

export interface AmbiguousContactItem {
  id?: number;
  name: string;
  phone: string;
  relationship?: string;
  email?: string;
}

interface ConfirmationModalProps {
  isOpen: boolean;
  prompt: string;
  intent: string;
  riskLevel: 'medium' | 'high';
  application?: string;
  recipient?: string;
  message?: string;
  phone?: string;
  ambiguousContacts?: AmbiguousContactItem[];
  onSelectContact?: (contactName: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  prompt,
  intent,
  riskLevel,
  application,
  recipient,
  message,
  phone,
  ambiguousContacts = [],
  onSelectContact,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  const isHighRisk = riskLevel === 'high';
  const isMessageAction = Boolean(
    recipient ||
    message ||
    intent === 'send_message' ||
    (application && application.toLowerCase().includes('whatsapp'))
  );
  const hasAmbiguous = Boolean(ambiguousContacts && ambiguousContacts.length > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden p-6 text-white">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div
            className={`p-3 rounded-xl flex-shrink-0 ${
              isMessageAction
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : isHighRisk
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
            }`}
          >
            {isMessageAction ? (
              <MessageCircle className="w-7 h-7" />
            ) : (
              <AlertTriangle className="w-7 h-7" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                  isMessageAction
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : isHighRisk
                    ? 'bg-red-500/20 text-red-300'
                    : 'bg-amber-500/20 text-amber-300'
                }`}
              >
                {isMessageAction ? 'Message Confirmation' : `${riskLevel} Risk Action`}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {intent || (isMessageAction ? 'send_message' : 'security_check')}
              </span>
            </div>
            <h3 className="text-lg font-bold text-white mt-1">
              {hasAmbiguous
                ? 'Select Recipient Contact'
                : isMessageAction
                ? 'Confirm WhatsApp Message'
                : 'Safety Confirmation Required'}
            </h3>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Ambiguous Contacts Selection Mode */}
        {hasAmbiguous ? (
          <div className="mt-4 space-y-3">
            <p className="text-slate-300 text-sm">
              {prompt || `Multiple contacts found. Please select the correct recipient:`}
            </p>
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {ambiguousContacts.map((c) => (
                <button
                  key={c.id || c.name}
                  onClick={() => onSelectContact && onSelectContact(c.name)}
                  className="w-full text-left p-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 hover:border-emerald-500/50 transition flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold text-xs">
                      <User className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-semibold text-white group-hover:text-emerald-300 transition text-sm">
                        {c.name}
                      </div>
                      <div className="text-xs text-slate-400">
                        {c.phone} {c.relationship ? `• ${c.relationship}` : ''}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20 group-hover:bg-emerald-500 group-hover:text-slate-950 transition">
                    Select
                  </span>
                </button>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-end">
              <button
                onClick={onCancel}
                className="px-4 py-2 rounded-xl text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : isMessageAction ? (
          /* Structured WhatsApp Message Confirmation Format */
          <div className="mt-4 space-y-4">
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-2.5">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400 font-medium">Recipient:</span>
                <span className="text-white font-semibold">
                  {recipient || 'Contact'}{' '}
                  {phone ? <span className="text-emerald-400 text-xs">({phone})</span> : null}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400 font-medium">Application:</span>
                <span className="text-emerald-400 font-semibold">{application || 'WhatsApp'}</span>
              </div>
              <div className="text-sm pt-1">
                <span className="text-slate-400 font-medium block mb-1">Message:</span>
                <div className="bg-slate-900/90 rounded-lg p-3 text-slate-100 border border-slate-700/70 font-mono text-sm whitespace-pre-wrap">
                  "{message || 'Hi'}"
                </div>
              </div>
            </div>

            <p className="text-xs text-slate-400">
              The assistant will activate WhatsApp and dispatch this verified message after your explicit confirmation.
            </p>

            {/* Action buttons: [Confirm and Send] [Cancel] */}
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={onCancel}
                className="px-4 py-2.5 rounded-xl text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-lg flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/30 transition"
              >
                <Send className="w-4 h-4" />
                Confirm and Send
              </button>
            </div>
          </div>
        ) : (
          /* General Security Confirmation */
          <div className="mt-4 space-y-4">
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
              <p className="text-slate-200 text-sm md:text-base font-medium">
                {prompt}
              </p>
            </div>

            <p className="text-xs text-slate-400">
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
                className={`px-5 py-2.5 rounded-xl text-sm font-semibold text-white shadow-lg flex items-center gap-2 transition ${
                  isHighRisk
                    ? 'bg-red-600 hover:bg-red-500 shadow-red-600/30'
                    : 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/30'
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                Confirm & Execute
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
