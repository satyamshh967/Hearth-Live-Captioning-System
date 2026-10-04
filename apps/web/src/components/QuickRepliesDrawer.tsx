import React, { useState } from 'react';
import { QuickReply } from '../types';
import { Volume2, Maximize2, X, MessageSquare } from 'lucide-react';

interface QuickRepliesDrawerProps {
  replies: QuickReply[];
  onDismiss: () => void;
}

export const QuickRepliesDrawer: React.FC<QuickRepliesDrawerProps> = ({
  replies,
  onDismiss,
}) => {
  const [fullscreenText, setFullscreenText] = useState<string | null>(null);

  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'hi-IN';
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  if (fullscreenText) {
    return (
      <div className="fixed inset-0 z-50 bg-amber-500 text-slate-950 flex flex-col justify-between p-8 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-end">
          <button
            onClick={() => setFullscreenText(null)}
            className="p-3 rounded-2xl bg-slate-950 text-amber-400 font-bold flex items-center space-x-2"
          >
            <X className="w-8 h-8" />
            <span className="text-xl">Close</span>
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center text-center">
          <div className="text-5xl sm:text-7xl font-extrabold tracking-tight leading-tight">
            {fullscreenText}
          </div>
        </div>
        <div className="text-center text-slate-900 font-semibold text-lg">
          Showing response card across table
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-slate-800 bg-slate-900/95 backdrop-blur px-4 py-3 z-10 shadow-2xl">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2 text-xs font-bold text-amber-400 uppercase tracking-wider">
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Dadaji's Quick Replies</span>
          </div>
          <button
            onClick={onDismiss}
            className="text-slate-400 hover:text-slate-200 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {replies.map((reply, idx) => (
            <div
              key={idx}
              className="flex flex-col justify-between p-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700 transition"
            >
              <div className="text-xs font-bold text-slate-400 mb-1">{reply.label}</div>
              <div className="text-base font-bold text-slate-100 mb-3 leading-snug">
                "{reply.text}"
              </div>
              <div className="flex items-center space-x-2 mt-auto">
                <button
                  onClick={() => speakText(reply.text)}
                  className="flex-1 flex items-center justify-center space-x-1 py-1.5 px-2 rounded-lg bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 text-xs font-semibold border border-indigo-700/50"
                  title="Speak response out loud"
                >
                  <Volume2 className="w-3.5 h-3.5" />
                  <span>Speak</span>
                </button>
                <button
                  onClick={() => setFullscreenText(reply.text)}
                  className="flex items-center justify-center p-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs border border-amber-500/40"
                  title="Show full screen across the table"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
