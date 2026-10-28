import React, { useState, useEffect } from 'react';
import { Bell, Plus, CheckCircle2, Clock, Trash2, Repeat } from 'lucide-react';
import { api } from '../services/api';
import { ReminderItem } from '../types';

export const RemindersPage: React.FC = () => {
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [title, setTitle] = useState('');
  const [dueTimeStr, setDueTimeStr] = useState('');
  const [isRecurring, setIsRecurring] = useState(false);

  const fetchReminders = async () => {
    try {
      const data = await api.getReminders(true);
      setReminders(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchReminders();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !dueTimeStr.trim()) return;

    try {
      const targetDate = new Date(dueTimeStr);
      await api.createReminder(
        title.trim(),
        targetDate.toISOString(),
        isRecurring,
        isRecurring ? 'daily' : undefined
      );
      setTitle('');
      setDueTimeStr('');
      setIsRecurring(false);
      setShowAddModal(false);
      fetchReminders();
    } catch (e) {
      alert('Error creating reminder');
    }
  };

  const handleToggle = async (id: number) => {
    await api.toggleReminderComplete(id);
    fetchReminders();
  };

  const handleDelete = async (id: number) => {
    await api.deleteReminder(id);
    setReminders((prev) => prev.filter((r) => r.id !== id));
  };

  const activeReminders = reminders.filter((r) => !r.is_completed);
  const completedReminders = reminders.filter((r) => r.is_completed);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
            <Bell className="w-6 h-6 text-pink-400" />
            Reminders & Schedule Hub
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Voice-managed alarms and automated desktop spoken notifications.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-pink-600 hover:bg-pink-500 text-white text-xs font-semibold shadow-lg shadow-pink-600/30 transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          Add Reminder
        </button>
      </div>

      {/* Active Reminders */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">
          Upcoming ({activeReminders.length})
        </h3>

        {activeReminders.length === 0 ? (
          <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 text-center text-slate-500 text-sm">
            No upcoming reminders. Say "Remind me to study at 8 PM" or click Add Reminder above!
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activeReminders.map((r) => (
              <div
                key={r.id}
                className="p-4 rounded-2xl bg-slate-900 border border-slate-800 hover:border-pink-500/30 flex items-start justify-between gap-3 transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggle(r.id)}
                      className="text-slate-500 hover:text-emerald-400 transition"
                      title="Mark Complete"
                    >
                      <CheckCircle2 className="w-5 h-5" />
                    </button>
                    <h4 className="font-semibold text-white text-sm">
                      {r.title}
                    </h4>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400 pl-7">
                    <Clock className="w-3.5 h-3.5 text-pink-400" />
                    <span>{new Date(r.due_time).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                    {r.is_recurring && (
                      <span className="flex items-center gap-1 text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                        <Repeat className="w-3 h-3" /> Daily
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(r.id)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 transition"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completed Reminders */}
      {completedReminders.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-slate-800/80">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
            Completed ({completedReminders.length})
          </h3>
          <div className="space-y-2">
            {completedReminders.map((r) => (
              <div
                key={r.id}
                className="p-3 rounded-xl bg-slate-900/50 border border-slate-800/60 flex items-center justify-between text-xs text-slate-400"
              >
                <div className="flex items-center gap-2 line-through">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span>{r.title}</span>
                </div>
                <button
                  onClick={() => handleDelete(r.id)}
                  className="p-1 text-slate-600 hover:text-red-400"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 text-white space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-pink-400" />
              New Reminder
            </h3>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Reminder Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Submit college assignment"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-pink-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Due Date & Time</label>
                <input
                  type="datetime-local"
                  required
                  value={dueTimeStr}
                  onChange={(e) => setDueTimeStr(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-pink-500"
                />
              </div>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isRecurring}
                  onChange={(e) => setIsRecurring(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-pink-500"
                />
                <span>Repeat Daily</span>
              </label>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-pink-600 hover:bg-pink-500 text-white"
                >
                  Save Reminder
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
