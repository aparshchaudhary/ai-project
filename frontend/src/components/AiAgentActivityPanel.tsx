import React from 'react';
import {
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Play,
  RotateCcw,
  Check,
  X,
  ExternalLink,
  MessageSquare,
  Search,
  Globe,
  Camera,
  UserCheck
} from 'lucide-react';
import { AgentTaskPlan, AgentTaskItem, AgentTaskStatus, ContactItem } from '../types';

interface AiAgentActivityPanelProps {
  plan: AgentTaskPlan | null;
  onConfirmPlan?: (planId: string, confirmationId?: string) => void;
  onCancelPlan?: (planId: string) => void;
  onRetryTask?: (taskId: string) => void;
  onSelectContact?: (contact: ContactItem) => void;
  onRunSampleCommand?: (text: string) => void;
}

export const AiAgentActivityPanel: React.FC<AiAgentActivityPanelProps> = ({
  plan,
  onConfirmPlan,
  onCancelPlan,
  onRetryTask,
  onSelectContact,
  onRunSampleCommand
}) => {
  const getStatusBadge = (status: AgentTaskStatus | string) => {
    switch (status) {
      case 'Completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        );
      case 'Running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 animate-pulse">
            <RotateCcw className="w-3.5 h-3.5 animate-spin" /> Running
          </span>
        );
      case 'Waiting for Confirmation':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" /> Awaiting Confirmation
          </span>
        );
      case 'Failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <X className="w-3.5 h-3.5" /> Failed
          </span>
        );
      case 'Skipped':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-yellow-500/15 text-yellow-400 border border-yellow-500/30">
            <Clock className="w-3.5 h-3.5" /> Skipped (Dependency)
          </span>
        );
      case 'Cancelled':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/15 text-slate-400 border border-slate-500/30">
            <X className="w-3.5 h-3.5" /> Cancelled
          </span>
        );
      case 'Planning':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
            <Cpu className="w-3.5 h-3.5 animate-spin" /> Planning
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3.5 h-3.5" /> Pending
          </span>
        );
    }
  };

  const getIntentIcon = (intent: string) => {
    switch (intent) {
      case 'open_application':
        return <ExternalLink className="w-4 h-4 text-cyan-400" />;
      case 'search_web':
        return <Search className="w-4 h-4 text-blue-400" />;
      case 'send_message':
        return <MessageSquare className="w-4 h-4 text-emerald-400" />;
      case 'summarize_results':
        return <Globe className="w-4 h-4 text-purple-400" />;
      case 'take_screenshot':
        return <Camera className="w-4 h-4 text-yellow-400" />;
      default:
        return <Layers className="w-4 h-4 text-slate-400" />;
    }
  };

  const sampleMultiCommands = [
    {
      title: "Chrome + WhatsApp + Search + Message",
      command: "Open Google Chrome and search for Artificial Intelligence, then open WhatsApp and send Hi to Ram."
    },
    {
      title: "Hinglish Multi-Command",
      command: "Chrome kholo aur AI ke baare mein search karo"
    },
    {
      title: "Concurrent Dual Launch",
      command: "Open Chrome and WhatsApp simultaneously."
    },
    {
      title: "Search & Web Summarize",
      command: "Search for AI agents and then summarize the results"
    }
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-xl transition-all">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-indigo-500/20 to-purple-500/20 border border-cyan-500/30 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-slate-100">
                AI Agent Multi-Command Engine
              </h3>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                Active DAG
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Parallel execution, dependency scheduling & cross-app automation
            </p>
          </div>
        </div>

        {plan && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-mono bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800">
              {plan.plan_id}
            </span>
            {getStatusBadge(plan.status === 'completed' ? 'Completed' : plan.status === 'running' ? 'Running' : plan.status === 'waiting_confirmation' ? 'Waiting for Confirmation' : plan.status)}
          </div>
        )}
      </div>

      {/* Active Plan Instruction Banner */}
      {plan ? (
        <div className="mt-4 p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Spoken Instruction
            </div>
            <p className="text-sm font-medium text-slate-200 italic">
              "{plan.original_instruction}"
            </p>
            {plan.summary && (
              <p className="text-xs text-cyan-300/90 pt-1">
                Summary: {plan.summary}
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-4 p-4 text-center rounded-xl border border-dashed border-slate-800 bg-slate-950/40">
          <Layers className="w-6 h-6 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-400">No active multi-command plan</p>
          <p className="text-xs text-slate-500 mt-1">
            Try speaking a compound sentence or select a quick demonstration below:
          </p>
        </div>
      )}

      {/* Ambiguity Resolution UI */}
      {plan?.ambiguous_contacts && plan.ambiguous_contacts.length > 1 && (
        <div className="mt-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 animate-fadeIn">
          <div className="flex items-center gap-2 text-amber-300 font-semibold text-sm mb-2">
            <UserCheck className="w-4 h-4 text-amber-400" />
            Multiple Contacts Found: Please Select Recipient
          </div>
          <p className="text-xs text-slate-300 mb-3">
            I found {plan.ambiguous_contacts.length} matching contacts. Click one or speak their name to select:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {plan.ambiguous_contacts.map((contact, idx) => (
              <button
                key={contact.id || idx}
                onClick={() => onSelectContact && onSelectContact(contact)}
                className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-amber-500/40 hover:border-amber-400 text-left transition-all group"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-100 group-hover:text-amber-300">
                    {contact.name}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {contact.phone} {contact.relationship ? `• ${contact.relationship}` : ''}
                  </div>
                </div>
                <span className="text-xs text-amber-400 font-medium px-2 py-0.5 rounded bg-amber-500/20">
                  Select [{idx + 1}]
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Confirmation Banner for Sensitive Actions */}
      {plan?.status === 'waiting_confirmation' && !plan?.ambiguous_contacts && (
        <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-purple-900/30 via-indigo-900/30 to-slate-900 border border-purple-500/40 flex flex-wrap items-center justify-between gap-3 animate-fadeIn">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-purple-300 text-sm font-semibold">
              <AlertTriangle className="w-4 h-4 text-purple-400" />
              Security Confirmation Required
            </div>
            <p className="text-xs text-slate-300">
              The agent is prepared to dispatch a WhatsApp message or external action. Do you authorize this operation?
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onConfirmPlan && onConfirmPlan(plan.plan_id, plan.confirmation_id)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/20 transition-all"
            >
              <Check className="w-3.5 h-3.5" />
              Confirm & Execute
            </button>
            <button
              onClick={() => onCancelPlan && onCancelPlan(plan.plan_id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all"
            >
              <X className="w-3.5 h-3.5" />
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Task DAG Step Pipeline */}
      {plan && plan.tasks.length > 0 && (
        <div className="mt-4 space-y-2.5">
          <div className="text-xs font-semibold text-slate-400 flex items-center justify-between">
            <span>Execution Pipeline ({plan.tasks.length} steps)</span>
            <span className="text-[11px] text-slate-500">
              DAG Flow: Dependent steps wait, independent run parallel
            </span>
          </div>

          <div className="space-y-2">
            {plan.tasks.map((task: AgentTaskItem, index: number) => {
              const hasFailed = task.status === 'Failed';
              const hasSkipped = task.status === 'Skipped';

              return (
                <div
                  key={task.id}
                  className={`p-3.5 rounded-xl border transition-all ${
                    hasFailed
                      ? 'bg-rose-950/20 border-rose-900/50'
                      : hasSkipped
                      ? 'bg-yellow-950/15 border-yellow-900/30 opacity-75'
                      : task.status === 'Completed'
                      ? 'bg-slate-950/60 border-slate-800'
                      : task.status === 'Running'
                      ? 'bg-cyan-950/20 border-cyan-800/60 ring-1 ring-cyan-500/30'
                      : 'bg-slate-950/40 border-slate-800/60'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center font-mono text-xs font-semibold text-slate-300">
                        {index + 1}
                      </div>
                      <div className="flex items-center gap-2">
                        {getIntentIcon(task.intent)}
                        <span className="text-sm font-medium text-slate-100">
                          {task.title}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {task.application && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800/90 text-slate-300 border border-slate-700">
                          app:{task.application}
                        </span>
                      )}
                      {task.depends_on && task.depends_on.length > 0 && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800/90 text-amber-300/80 border border-slate-700">
                          depends:{task.depends_on.join(',')}
                        </span>
                      )}
                      {getStatusBadge(task.status)}
                    </div>
                  </div>

                  {/* Task details / results / errors */}
                  <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
                    <div className="flex-1">
                      {task.result && (
                        <p className="text-emerald-400 font-medium">
                          ✓ {task.result}
                        </p>
                      )}
                      {task.error && (
                        <p className="text-rose-400 font-medium">
                          ⚠ {task.error}
                        </p>
                      )}
                      {!task.result && !task.error && (
                        <p className="text-slate-500">
                          {task.query
                            ? `Query: "${task.query}"`
                            : task.contact
                            ? `Recipient: ${task.contact} | Message: "${task.message}"`
                            : 'Ready for execution'}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      {task.execution_time_ms !== undefined && task.execution_time_ms !== null && (
                        <span className="font-mono text-[11px] text-slate-500">
                          {task.execution_time_ms.toFixed(1)} ms
                        </span>
                      )}
                      {hasFailed && onRetryTask && (
                        <button
                          onClick={() => onRetryTask(task.id)}
                          className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 underline"
                        >
                          <RotateCcw className="w-3 h-3" /> Retry step
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Demo Multi-Command Chips */}
      <div className="mt-5 pt-4 border-t border-slate-800">
        <div className="text-xs font-semibold text-slate-400 mb-2 flex items-center gap-1.5">
          <Play className="w-3.5 h-3.5 text-cyan-400" />
          Test Multi-Command Presets
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {sampleMultiCommands.map((sample, idx) => (
            <button
              key={idx}
              onClick={() => onRunSampleCommand && onRunSampleCommand(sample.command)}
              className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-cyan-500/40 text-left transition-all hover:bg-slate-800/40 group"
            >
              <div className="text-xs font-medium text-cyan-300 group-hover:text-cyan-200">
                {sample.title}
              </div>
              <div className="text-[11px] text-slate-400 truncate mt-0.5 font-mono">
                "{sample.command}"
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
