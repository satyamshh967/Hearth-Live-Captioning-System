import React from 'react';
import { Bell, X } from 'lucide-react';

interface AddressedAlertBannerProps {
  vocative: string;
  onDismiss: () => void;
}

export const AddressedAlertBanner: React.FC<AddressedAlertBannerProps> = ({
  vocative,
  onDismiss,
}) => {
  return (
    <div className="fixed top-16 left-0 right-0 z-30 flex justify-center px-4 animate-in fade-in slide-in-from-top-4 duration-300 pointer-events-none">
      <div className="pointer-events-auto flex items-center space-x-3 px-5 py-3 rounded-2xl bg-amber-500 text-slate-950 font-bold shadow-2xl border-2 border-amber-300 max-w-md w-full justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-slate-950 text-amber-400">
            <Bell className="w-6 h-6 animate-bounce" />
          </div>
          <div>
            <div className="text-sm uppercase tracking-wider text-slate-900 font-extrabold">
              Addressed To You
            </div>
            <div className="text-lg">
              Someone called: <span className="underline decoration-slate-950">{vocative}</span>
            </div>
          </div>
        </div>
        <button
          onClick={onDismiss}
          className="p-1.5 rounded-lg bg-amber-600/30 hover:bg-amber-600/50 text-slate-950 transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
