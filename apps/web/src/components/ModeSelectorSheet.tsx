import React from 'react';
import {
  Subtitles,
  Headphones,
  Users2,
  FileText,
  Sliders,
  Check,
  X,
  Languages,
  ArrowRightLeft,
} from 'lucide-react';
import { AppMode } from '../types';

interface ModeSelectorSheetProps {
  isOpen: boolean;
  onClose: () => void;
  activeMode: AppMode;
  onSelectMode: (mode: AppMode) => void;
  sourceLang: string;
  targetLang: string;
  onSelectSourceLang: (lang: string) => void;
  onSelectTargetLang: (lang: string) => void;
  onSwapLanguages: () => void;
}

const MODES: {
  id: AppMode;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  tag: string;
}[] = [
  {
    id: 'captions',
    title: 'Live Captions',
    description: 'Real-time same-language transcription with speaker tracking and personal vocabulary.',
    icon: Subtitles,
    tag: 'Same Language',
  },
  {
    id: 'listening',
    title: 'Live Listening',
    description: 'Listen to foreign speakers; read real-time translated captions in your language.',
    icon: Headphones,
    tag: 'One-Way Translate',
  },
  {
    id: 'conversation',
    title: 'Face-to-Face Split',
    description: '180° inverted split screen for face-to-face two-way table conversation across two languages.',
    icon: Users2,
    tag: 'Two-Way Table',
  },
  {
    id: 'text_only',
    title: 'Text Only Display',
    description: 'High-contrast silent visual stream with pure translated text and zero audio cues.',
    icon: FileText,
    tag: 'Silent Focus',
  },
  {
    id: 'custom',
    title: 'Custom Engine Settings',
    description: 'Full control over speed-vs-accuracy, active profiles, TTS speed, and layout options.',
    icon: Sliders,
    tag: 'Personalized',
  },
];

const AVAILABLE_LANGUAGES = [
  { code: 'auto', name: 'Auto-Detect' },
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish (Español)' },
  { code: 'hi', name: 'Hindi (हिन्दी)' },
  { code: 'fr', name: 'French (Français)' },
  { code: 'de', name: 'German (Deutsch)' },
];

export const ModeSelectorSheet: React.FC<ModeSelectorSheetProps> = ({
  isOpen,
  onClose,
  activeMode,
  onSelectMode,
  sourceLang,
  targetLang,
  onSelectSourceLang,
  onSelectTargetLang,
  onSwapLanguages,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm transition-opacity">
      <div
        className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-t-[24px] sm:rounded-[24px] p-6 shadow-2xl overflow-y-auto max-h-[90vh] transition-transform duration-200"
        role="dialog"
        aria-modal="true"
        aria-label="Select Hearth Operation Mode"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center space-x-2">
              <Languages className="w-5 h-5 text-amber-400" />
              <span>Translation & Operation Modes</span>
            </h2>
            <p className="text-sm text-slate-400">
              Select how Hearth captures, translates, and displays conversation.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Language Pair Selector */}
        <div className="my-5 p-4 rounded-2xl bg-slate-950/80 border border-slate-800">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Language Pair
          </label>
          <div className="flex items-center space-x-3">
            <select
              value={sourceLang}
              onChange={(e) => onSelectSourceLang(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-white font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              {AVAILABLE_LANGUAGES.map((l) => (
                <option key={`src-${l.code}`} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>

            <button
              onClick={onSwapLanguages}
              disabled={sourceLang === 'auto'}
              className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 transition"
              title="Swap languages"
            >
              <ArrowRightLeft className="w-4 h-4" />
            </button>

            <select
              value={targetLang}
              onChange={(e) => onSelectTargetLang(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-white font-medium focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              {AVAILABLE_LANGUAGES.filter((l) => l.code !== 'auto').map((l) => (
                <option key={`tgt-${l.code}`} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Mode Radio Cards */}
        <div className="space-y-3">
          {MODES.map((m) => {
            const isSelected = activeMode === m.id;
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                onClick={() => {
                  onSelectMode(m.id);
                  onClose();
                }}
                className={`w-full flex items-start space-x-4 p-4 rounded-2xl border text-left transition-all ${
                  isSelected
                    ? 'bg-amber-500/10 border-amber-500/60 ring-1 ring-amber-500/50 shadow-md'
                    : 'bg-slate-950/40 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
                }`}
              >
                <div
                  className={`p-3 rounded-xl ${
                    isSelected
                      ? 'bg-amber-500 text-slate-950'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-white text-base">
                      {m.title}
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                      {m.tag}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    {m.description}
                  </p>
                </div>
                {isSelected && (
                  <div className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center text-slate-950 flex-shrink-0 mt-1">
                    <Check className="w-4 h-4 stroke-[3]" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
