import React, { useEffect, useRef, useState } from 'react';
import { Utterance, WordItem } from '../types';
import { ChevronDown, Edit2, Stethoscope, Languages } from 'lucide-react';

interface CaptionStreamProps {
  utterances: Utterance[];
  partialText: string;
  fontSize: number;
  fontFamily: 'sans' | 'dyslexic';
  lowConfidenceUnderline: boolean;
  plainLanguageMode: boolean;
  onCorrectWord: (word: string, context: string) => void;
  onRenameSpeaker: (speakerId: string, currentName: string) => void;
  onRequestPlainLanguage: (uttId: string, text: string) => void;
}

const SPEAKER_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Priya: { bg: 'bg-emerald-950/40', text: 'text-emerald-300', border: 'border-emerald-700/50' },
  Rohan: { bg: 'bg-sky-950/40', text: 'text-sky-300', border: 'border-sky-700/50' },
  Dadaji: { bg: 'bg-amber-950/50', text: 'text-amber-300', border: 'border-amber-600/70' },
  Sunita: { bg: 'bg-rose-950/40', text: 'text-rose-300', border: 'border-rose-700/50' },
  'Doctor Verma': { bg: 'bg-teal-950/50', text: 'text-teal-300', border: 'border-teal-600/70' },
  'Speaker 1': { bg: 'bg-indigo-950/40', text: 'text-indigo-300', border: 'border-indigo-700/50' },
  'Speaker 2': { bg: 'bg-violet-950/40', text: 'text-violet-300', border: 'border-violet-700/50' },
  'Speaker 3': { bg: 'bg-amber-950/40', text: 'text-amber-300', border: 'border-amber-700/50' },
  'Speaker 4': { bg: 'bg-fuchsia-950/40', text: 'text-fuchsia-300', border: 'border-fuchsia-700/50' },
};

function getSpeakerColor(speaker: string) {
  if (SPEAKER_COLORS[speaker]) return SPEAKER_COLORS[speaker];
  return { bg: 'bg-slate-900/60', text: 'text-slate-300', border: 'border-slate-700' };
}

export const CaptionStream: React.FC<CaptionStreamProps> = ({
  utterances,
  partialText,
  fontSize,
  fontFamily,
  lowConfidenceUnderline,
  plainLanguageMode,
  onCorrectWord,
  onRenameSpeaker,
  onRequestPlainLanguage,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll handler
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [utterances, partialText, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 60;
    setAutoScroll(isAtBottom);
  };

  const resumeScroll = () => {
    setAutoScroll(true);
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  };

  return (
    <div className="relative flex-1 h-full overflow-hidden flex flex-col bg-slate-950">
      {/* Scrollable conversation stream */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-5"
      >
        {utterances.length === 0 && !partialText && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto text-slate-500">
            <div className="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mb-4 text-amber-500">
              <span className="text-2xl font-bold">H</span>
            </div>
            <h3 className="text-xl font-bold text-slate-300 mb-2">Hearth is Ready</h3>
            <p className="text-base text-slate-400">
              Press <span className="text-amber-400 font-semibold">Start Captions</span> above to begin listening. Captions will appear here in large, high-contrast type.
            </p>
          </div>
        )}

        {utterances.map((utt) => {
          const color = getSpeakerColor(utt.speaker);

          return (
            <div
              key={utt.utt_id}
              className={`rounded-2xl p-4 sm:p-5 transition-all border ${color.bg} ${color.border} ${
                utt.addressed_to_me ? 'ring-2 ring-amber-400/80' : ''
              }`}
            >
              {/* Speaker header row */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className={`font-bold text-sm sm:text-base ${color.text}`}>
                    {utt.speaker}
                  </span>
                  <button
                    onClick={() => onRenameSpeaker(utt.speaker_id || utt.speaker, utt.speaker)}
                    className="p-1 text-slate-500 hover:text-slate-300 rounded transition"
                    title="Rename this speaker"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  {utt.addressed_to_me && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold">
                      Addressed to you
                    </span>
                  )}
                  {utt.task === 'translate' && (
                    <span className="flex items-center space-x-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40 font-semibold">
                      <Languages className="w-3 h-3" />
                      <span>Translated to English</span>
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2 text-xs text-slate-400">
                  {utt.latency_ms && (
                    <span>{utt.latency_ms.toFixed(0)}ms</span>
                  )}
                  {plainLanguageMode && !utt.plain_text && (
                    <button
                      onClick={() => onRequestPlainLanguage(utt.utt_id, utt.text)}
                      className="flex items-center space-x-1 px-2 py-0.5 rounded bg-teal-950/60 border border-teal-800 text-teal-300 hover:bg-teal-900"
                    >
                      <Stethoscope className="w-3 h-3" />
                      <span>Simplify</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Main caption text */}
              <div
                style={{ fontSize: `${fontSize}px`, lineHeight: 1.4 }}
                className={`font-semibold tracking-wide text-slate-100 ${
                  fontFamily === 'dyslexic' ? 'font-dyslexic' : 'font-sans'
                }`}
              >
                {utt.words && utt.words.length > 0 ? (
                  utt.words.map((w: WordItem, idx: number) => {
                    const isLowConf = lowConfidenceUnderline && w.conf < 0.70;
                    return (
                      <span
                        key={idx}
                        onClick={() => onCorrectWord(w.w, utt.text)}
                        className={`inline-block mr-1.5 cursor-pointer rounded px-0.5 hover:bg-amber-500/20 hover:text-amber-200 transition ${
                          isLowConf ? 'underline decoration-dotted decoration-amber-400/70 text-slate-300' : ''
                        }`}
                        title={`Tap to fix word (${(w.conf * 100).toFixed(0)}% conf)`}
                      >
                        {w.w}
                      </span>
                    );
                  })
                ) : (
                  <span>{utt.text}</span>
                )}
              </div>

              {/* Simplified plain language box (Doctor visit mode) */}
              {plainLanguageMode && utt.plain_text && (
                <div className="mt-3 p-3 rounded-xl bg-teal-950/70 border border-teal-700/60 text-teal-100">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-teal-300 mb-1">
                    <Stethoscope className="w-3.5 h-3.5" />
                    <span>Plain Language Summary</span>
                  </div>
                  <div
                    style={{ fontSize: `${Math.max(18, fontSize - 4)}px` }}
                    className="font-medium"
                  >
                    {utt.plain_text}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Rolling Partial Caption Bubble */}
        {partialText && (
          <div className="rounded-2xl p-4 sm:p-5 bg-slate-900/60 border border-slate-700/60 animate-pulse">
            <div className="flex items-center space-x-2 mb-2">
              <span className="font-bold text-sm text-amber-400">Listening...</span>
            </div>
            <div
              style={{ fontSize: `${fontSize}px`, lineHeight: 1.4 }}
              className={`font-medium text-slate-300 italic ${
                fontFamily === 'dyslexic' ? 'font-dyslexic' : 'font-sans'
              }`}
            >
              {partialText}
            </div>
          </div>
        )}
      </div>

      {/* Floating Resume Auto-Scroll Button */}
      {!autoScroll && (
        <button
          onClick={resumeScroll}
          className="absolute bottom-5 right-6 flex items-center space-x-2 px-4 py-2.5 rounded-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold shadow-xl border border-amber-300 transition-all z-10"
        >
          <ChevronDown className="w-5 h-5 animate-bounce" />
          <span>Resume Scroll</span>
        </button>
      )}
    </div>
  );
};
