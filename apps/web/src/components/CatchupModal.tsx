import React from 'react';
import { Sparkles, X, Users, RefreshCw } from 'lucide-react';

interface CatchupModalProps {
  isOpen: boolean;
  onClose: () => void;
  recapText: string;
  topic?: string;
  speakers?: string[];
  isLoading: boolean;
  onRefresh: () => void;
}

export const CatchupModal: React.FC<CatchupModalProps> = ({
  isOpen,
  onClose,
  recapText,
  topic,
  speakers,
  isLoading,
  onRefresh,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 sm:p-8 max-w-xl w-full shadow-2xl relative">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">What Did I Miss?</h3>
              <p className="text-sm text-slate-400">2-sentence recap of the last 60–90 seconds</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
            <p className="text-slate-400 font-medium">Catching up on recent conversation...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {topic && (
              <div className="inline-block px-3 py-1 rounded-full bg-indigo-950 border border-indigo-700/60 text-xs font-bold text-indigo-300">
                Topic: {topic}
              </div>
            )}

            <div className="p-5 rounded-2xl bg-indigo-950/30 border border-indigo-800/40 text-slate-100 text-xl sm:text-2xl font-semibold leading-relaxed">
              {recapText || "No recent conversation detected yet. Hearth starts recapping once family members speak."}
            </div>

            {speakers && speakers.length > 0 && (
              <div className="flex items-center space-x-2 text-sm text-slate-400">
                <Users className="w-4 h-4 text-indigo-400" />
                <span>Speakers: <strong className="text-slate-200">{speakers.join(', ')}</strong></span>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
              <button
                onClick={onRefresh}
                className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-sm transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Refresh Recap</span>
              </button>
              <button
                onClick={onClose}
                className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition"
              >
                Got It
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
