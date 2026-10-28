import React from 'react';
import {
  LayoutDashboard,
  Mic,
  History,
  Bell,
  Grid,
  BarChart3,
  Settings,
  HelpCircle,
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'assistant'
  | 'history'
  | 'reminders'
  | 'apps'
  | 'analytics'
  | 'settings'
  | 'help';

interface SidebarProps {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  pendingRemindersCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  pendingRemindersCount = 0,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'assistant', label: 'Live Assistant', icon: Mic, badge: 'Voice' },
    { id: 'history', label: 'Command History', icon: History },
    { id: 'reminders', label: 'Reminders', icon: Bell, count: pendingRemindersCount },
    { id: 'apps', label: 'Applications', icon: Grid },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'help', label: 'Help & Guide', icon: HelpCircle },
  ];

  return (
    <aside className="w-20 md:w-64 bg-slate-900/95 dark:bg-slate-900/95 border-r border-slate-800 flex flex-col justify-between py-5 px-3 text-slate-300 select-none">
      <div className="space-y-1">
        <div className="px-3 pb-3 hidden md:block">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Control Center
          </p>
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id as NavTab)}
              className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group relative ${isActive ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-600/25' : 'hover:bg-slate-800/80 text-slate-400 hover:text-slate-100'}`}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-blue-400'}`} />
              
              <span className="hidden md:inline truncate">{item.label}</span>

              {item.badge && (
                <span className="hidden md:inline ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 border border-cyan-400/30">
                  {item.badge}
                </span>
              )}

              {item.count !== undefined && item.count > 0 && (
                <span className="hidden md:inline ml-auto text-xs font-bold px-2 py-0.5 rounded-full bg-blue-500 text-white">
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="hidden md:block px-3 py-3 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-400">
        <p className="font-semibold text-slate-300">Desktop Automation</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Secure AI intent pipeline active.</p>
      </div>
    </aside>
  );
};
