import React, { useEffect, useRef, useState } from 'react';
import { Utterance, StreamingState } from '../types';
import { ChevronDown, Edit2, Stethoscope, Languages, Volume2 } from 'lucide-react';

interface CaptionStreamProps {
  utterances: Utterance[];
  streamingState?: StreamingState | null;
  fontSize: number;
  fontFamily: 'sans' | 'dyslexic';
  lowConfidenceUnderline: boolean;
  plainLanguageMode?: boolean;
  onCorrectWord: (word: string, context: string) => void;
  onRenameSpeaker: (speakerId: string, currentName: string) => void;
  onRequestPlainLanguage?: (uttId: string, text: string) => void;
  onSpeakText?: (text: string, lang: string) => void;
}

const PALETTE = [
  { bg: 'bg-amber-950/40', text: 'text-amber-300', border: 'border-amber-600/60' },
  { bg: 'bg-emerald-950/40', text: 'text-emerald-300', border: 'border-emerald-600/60' },
  { bg: 'bg-sky-950/40', text: 'text-sky-300', border: 'border-sky-600/60' },
  { bg: 'bg-indigo-950/40', text: 'text-indigo-300', border: 'border-indigo-600/60' },
  { bg: 'bg-rose-950/40', text: 'text-rose-300', border: 'border-rose-600/60' },
  { bg: 'bg-teal-950/40', text: 'text-teal-300', border: 'border-teal-600/60' },
];

function getSpeakerColor(speaker: string) {
  let hash = 0;
  for (let i = 0; i < speaker.length; i++) {
    hash = (hash << 5) - hash + speaker.charCodeAt(i);
  }
  const idx = Math.abs(hash) % PALETTE.length;
  return PALETTE[idx];
}

export const CaptionStream: React.FC<CaptionStreamProps> = ({
  utterances,
  streamingState,
  fontSize,
  fontFamily,
  lowConfidenceUnderline,
  plainLanguageMode = false,
  onCorrectWord,
  onRenameSpeaker,
  onRequestPlainLanguage,
  onSpeakText,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll handler (anchors newest line at bottom)
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [utterances, streamingState, autoScroll]);

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
      {/* Scrollable Container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className={`flex-1 overflow-y-auto px-4 py-6 space-y-6 ${
          fontFamily === 'dyslexic' ? 'font-dyslexic' : 'font-sans'
        }`}
      >
        {utterances.length === 0 && (!streamingState || (!streamingState.committed_source && !streamingState.tentative_source)) && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-3 select-none">
            <div className="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-600">
              <Languages className="w-8 h-8 text-amber-500/40" />
            </div>
            <p className="text-lg font-medium">Hearth is ready. Tap Start to begin live captions.</p>
            <p className="text-xs text-slate-600">Words appear live while speech is in progress.</p>
          </div>
        )}

        {/* Committed Utterances */}
        {utterances.map((utt) => {
          const color = getSpeakerColor(utt.speaker);
          return (
            <div
              key={utt.utt_id}
              className={`p-5 rounded-2xl border transition-all ${color.bg} ${color.border} ${
                utt.addressed_to_me ? 'ring-2 ring-amber-400/80 shadow-lg shadow-amber-500/10' : ''
              }`}
            >
              {/* Speaker Header */}
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/40">
                <button
                  onClick={() => onRenameSpeaker(utt.speaker_id || utt.speaker, utt.speaker)}
                  className="flex items-center space-x-1.5 font-bold text-sm tracking-wide text-white hover:underline focus:outline-none"
                  title="Click to rename speaker"
                >
                  <span className={color.text}>{utt.speaker}</span>
                  <Edit2 className="w-3.5 h-3.5 text-slate-400 opacity-60 hover:opacity-100" />
                </button>

                <div className="flex items-center space-x-3 text-xs text-slate-400">
                  {utt.task === 'translate' && (
                    <span className="flex items-center space-x-1 text-indigo-400 bg-indigo-950/60 border border-indigo-700/40 px-2 py-0.5 rounded-full font-semibold">
                      <Languages className="w-3 h-3" />
                      <span>Translated to English</span>
                    </span>
                  )}
                  {onSpeakText && (
                    <button
                      onClick={() => onSpeakText(utt.translated_text || utt.text, utt.lang)}
                      className="p-1 text-slate-400 hover:text-white rounded"
                      title="Speak caption"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Source Text with Click-to-Correct Words */}
              <div
                style={{ fontSize: `${fontSize}px`, lineHeight: 1.35 }}
                className="font-bold text-white tracking-wide select-text"
              >
                {utt.words && utt.words.length > 0 ? (
                  utt.words.map((w, wIdx) => {
                    const isLowConf = lowConfidenceUnderline && w.conf < 0.65;
                    return (
                      <span
                        key={wIdx}
                        onClick={() => onCorrectWord(w.w, utt.text)}
                        className={`inline-block mr-1.5 cursor-pointer rounded px-0.5 hover:bg-amber-400/20 transition-all ${
                          isLowConf ? 'underline decoration-dotted decoration-amber-400/80' : ''
                        }`}
                        title={`Confidence: ${(w.conf * 100).toFixed(0)}%. Tap to correct.`}
                      >
                        {w.w}
                      </span>
                    );
                  })
                ) : (
                  <span>{utt.text}</span>
                )}
              </div>

              {/* Stacked Translation Line */}
              {utt.translated_text && (
                <div
                  style={{ fontSize: `${Math.max(16, fontSize * 0.85)}px`, lineHeight: 1.35 }}
                  className="mt-2.5 pt-2 border-t border-slate-800/40 font-semibold text-indigo-200 tracking-wide select-text opacity-90"
                >
                  {utt.translated_text}
                </div>
              )}

              {/* Doctor Visit / Plain Language Translation Box */}
              {utt.plain_text && (
                <div className="mt-3 p-3.5 rounded-xl bg-teal-950/60 border border-teal-600/50 text-teal-200 text-sm">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-teal-400 uppercase tracking-wider mb-1">
                    <Stethoscope className="w-3.5 h-3.5" />
                    <span>Plain Language Explanation</span>
                  </div>
                  <p className="font-medium leading-relaxed">{utt.plain_text}</p>
                </div>
              )}

              {plainLanguageMode && !utt.plain_text && onRequestPlainLanguage && (
                <button
                  onClick={() => onRequestPlainLanguage(utt.utt_id, utt.text)}
                  className="mt-2 text-xs flex items-center space-x-1 text-teal-400 hover:text-teal-300 bg-teal-950/40 border border-teal-700/40 px-2.5 py-1 rounded-lg transition"
                >
                  <Stethoscope className="w-3.5 h-3.5" />
                  <span>Simplify (Plain Language)</span>
                </button>
              )}
            </div>
          );
        })}

        {/* Live Streaming Active Bubble (Words committed are solid; tentative tail is ~55% opacity) */}
        {streamingState && (streamingState.committed_source || streamingState.tentative_source) && (
          <div className="p-5 rounded-2xl border bg-slate-900/70 border-amber-500/50 shadow-lg shadow-amber-500/5">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block" />
                <span>{streamingState.speaker || 'Speaking...'} (Live)</span>
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {streamingState.source_lang ? `${streamingState.source_lang.toUpperCase()} ` : ''}Streaming
              </span>
            </div>

            {/* Source Speech Stream */}
            <div
              style={{ fontSize: `${fontSize}px`, lineHeight: 1.35 }}
              className="font-bold tracking-wide transition-opacity duration-80"
            >
              <span className="text-white">{streamingState.committed_source} </span>
              <span className="text-slate-400 opacity-55 italic font-normal">
                {streamingState.tentative_source}
              </span>
            </div>

            {/* Stacked Translation Stream */}
            {(streamingState.committed_translated || streamingState.tentative_translated) && (
              <div
                style={{ fontSize: `${Math.max(16, fontSize * 0.85)}px`, lineHeight: 1.35 }}
                className="mt-2.5 pt-2 border-t border-slate-800 font-semibold tracking-wide"
              >
                <span className="text-indigo-200">{streamingState.committed_translated} </span>
                <span className="text-indigo-400 opacity-55 italic font-normal">
                  {streamingState.tentative_translated}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Resume Auto-Scroll Button */}
      {!autoScroll && (
        <button
          onClick={resumeScroll}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 flex items-center space-x-1.5 px-4 py-2 rounded-full bg-amber-500 text-slate-950 font-bold text-xs shadow-xl hover:bg-amber-400 transition-all animate-bounce"
        >
          <ChevronDown className="w-4 h-4" />
          <span>Resume Scroll</span>
        </button>
      )}
    </div>
  );
};
