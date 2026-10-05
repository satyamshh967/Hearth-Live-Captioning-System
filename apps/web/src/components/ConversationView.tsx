import React from 'react';
import { Utterance, StreamingState } from '../types';
import { RotateCw, Volume2, ArrowUpDown } from 'lucide-react';

interface ConversationViewProps {
  utterances: Utterance[];
  streamingState?: StreamingState | null;
  sourceLang: string;
  targetLang: string;
  fontSize: number;
  onSpeakText?: (text: string, lang: string) => void;
}

export const ConversationView: React.FC<ConversationViewProps> = ({
  utterances,
  streamingState,
  sourceLang,
  targetLang,
  fontSize,
  onSpeakText,
}) => {
  const recentUtterances = utterances.slice(-6);

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden select-none">
      {/* Top Half: Rotated 180° for the person sitting across the table */}
      <div className="flex-1 border-b-2 border-dashed border-amber-500/40 p-6 flex flex-col justify-end rotate-180 bg-slate-900/30 overflow-y-auto">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/60 opacity-60">
          <div className="flex items-center space-x-2">
            <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-700/50">
              Partner ({targetLang.toUpperCase()})
            </span>
            <span className="text-xs text-slate-400">180° Inverted Table View</span>
          </div>
          <RotateCw className="w-4 h-4 text-slate-500" />
        </div>

        <div className="space-y-3">
          {recentUtterances.map((utt) => (
            <div key={`top-${utt.utt_id}`} className="space-y-1">
              <div className="text-xs font-semibold text-indigo-400">{utt.speaker}</div>
              <div
                style={{ fontSize: `${Math.max(18, fontSize * 0.85)}px` }}
                className="font-bold text-white leading-snug"
              >
                {utt.translated_text || utt.text}
              </div>
            </div>
          ))}

          {/* Live streaming update */}
          {streamingState && (streamingState.committed_translated || streamingState.tentative_translated) && (
            <div className="space-y-1">
              <div className="text-xs font-semibold text-amber-400">
                {streamingState.speaker || 'Speaking...'}
              </div>
              <div
                style={{ fontSize: `${Math.max(18, fontSize * 0.85)}px` }}
                className="font-bold leading-snug"
              >
                <span className="text-white">{streamingState.committed_translated} </span>
                <span className="text-slate-400 opacity-60 italic">{streamingState.tentative_translated}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Center Divider with Language Tags */}
      <div className="h-10 bg-slate-900 border-y border-slate-800 flex items-center justify-between px-6 z-10 shadow-md">
        <span className="text-xs font-bold text-indigo-400">
          Partner: {targetLang.toUpperCase()}
        </span>
        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <ArrowUpDown className="w-4 h-4 text-amber-400" />
          <span>Face-to-Face Split Table</span>
        </div>
        <span className="text-xs font-bold text-amber-400">
          You: {sourceLang.toUpperCase()}
        </span>
      </div>

      {/* Bottom Half: Normal orientation for you */}
      <div className="flex-1 p-6 flex flex-col justify-end bg-slate-950 overflow-y-auto">
        <div className="space-y-3">
          {recentUtterances.map((utt) => (
            <div key={`bot-${utt.utt_id}`} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-amber-400">{utt.speaker}</span>
                {onSpeakText && (
                  <button
                    onClick={() => onSpeakText(utt.text, sourceLang)}
                    className="p-1 rounded text-slate-400 hover:text-white"
                  >
                    <Volume2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              <div
                style={{ fontSize: `${fontSize}px` }}
                className="font-bold text-white leading-snug"
              >
                {utt.text}
              </div>
              {utt.translated_text && (
                <div className="text-sm text-indigo-300 font-medium opacity-80">
                  {utt.translated_text}
                </div>
              )}
            </div>
          ))}

          {/* Live streaming update */}
          {streamingState && (streamingState.committed_source || streamingState.tentative_source) && (
            <div className="space-y-1">
              <div className="text-xs font-semibold text-amber-400">
                {streamingState.speaker || 'Speaking...'}
              </div>
              <div
                style={{ fontSize: `${fontSize}px` }}
                className="font-bold leading-snug"
              >
                <span className="text-white">{streamingState.committed_source} </span>
                <span className="text-slate-400 opacity-60 italic">{streamingState.tentative_source}</span>
              </div>
              {streamingState.committed_translated && (
                <div className="text-sm text-indigo-300 font-medium opacity-80">
                  {streamingState.committed_translated}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
