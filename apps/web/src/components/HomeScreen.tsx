import React from 'react';
import {
  Subtitles,
  Headphones,
  Users2,
  FileText,
  Sliders,
  Check,
  ArrowRightLeft,
  Play,
  ShieldCheck,
  Cpu,
} from 'lucide-react';
import { AppMode } from '../types';

interface HomeScreenProps {
  onStart: () => void;
  activeMode: AppMode;
  onSelectMode: (mode: AppMode) => void;
  sourceLang: string;
  targetLang: string;
  onSelectSourceLang: (lang: string) => void;
  onSelectTargetLang: (lang: string) => void;
  onSwapLanguages: () => void;
  modelProfile: string;
  activeProfileName: string;
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
    description: 'Sub-500ms same-language captions with speaker chips and domain vocabulary.',
    icon: Subtitles,
    tag: 'Same Language',
  },
  {
    id: 'listening',
    title: 'Live Listening',
    description: 'Listen to foreign speakers; read real-time translated captions on screen.',
    icon: Headphones,
    tag: 'One-Way Translate',
  },
  {
    id: 'conversation',
    title: 'Conversation Split',
    description: '180° inverted split screen for face-to-face table conversations across 2 languages.',
    icon: Users2,
    tag: 'Two-Way Table',
  },
  {
    id: 'text_only',
    title: 'Text Only',
    description: 'Silent high-contrast visual display with pure translation and zero audio output.',
    icon: FileText,
    tag: 'Silent Focus',
  },
  {
    id: 'custom',
    title: 'Custom Engine',
    description: 'Adjust model profile, TTS voice, speed-vs-accuracy, and terminology protection.',
    icon: Sliders,
    tag: 'Settings',
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

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onStart,
  activeMode,
  onSelectMode,
  sourceLang,
  targetLang,
  onSelectSourceLang,
  onSelectTargetLang,
  onSwapLanguages,
  modelProfile,
  activeProfileName,
}) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8 max-w-4xl mx-auto w-full select-none overflow-y-auto">
      {/* Brand & Readiness Badge */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 text-xs font-semibold mb-3">
          <ShieldCheck className="w-4 h-4" />
          <span>Local Engine · Zero Cloud Telemetry · Offline Ready</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Hearth Live
        </h1>
        <p className="text-slate-400 text-sm sm:text-base mt-1">
          Private, live captioning and instant offline speech translation for conversations.
        </p>
      </div>

      {/* Language Pair Selector Row */}
      <div className="w-full p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl mb-6 backdrop-blur">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Language Pair
          </label>
          <span className="text-xs text-amber-400 font-medium">
            Profile: {activeProfileName}
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={sourceLang}
            onChange={(e) => onSelectSourceLang(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-white font-semibold text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
          >
            {AVAILABLE_LANGUAGES.map((l) => (
              <option key={`home-src-${l.code}`} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>

          <button
            onClick={onSwapLanguages}
            disabled={sourceLang === 'auto'}
            className="p-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 transition shadow"
            title="Swap Source and Target Languages"
          >
            <ArrowRightLeft className="w-5 h-5 text-amber-400" />
          </button>

          <select
            value={targetLang}
            onChange={(e) => onSelectTargetLang(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-white font-semibold text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
          >
            {AVAILABLE_LANGUAGES.filter((l) => l.code !== 'auto').map((l) => (
              <option key={`home-tgt-${l.code}`} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Mode List as Radio Cards */}
      <div className="w-full space-y-3 mb-6">
        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
          Select Operation Mode
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {MODES.map((m) => {
            const isSelected = activeMode === m.id;
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                onClick={() => onSelectMode(m.id)}
                className={`flex items-start space-x-3.5 p-4 rounded-2xl border text-left transition-all ${
                  isSelected
                    ? 'bg-amber-500/10 border-amber-500/70 ring-1 ring-amber-500/50 shadow-lg'
                    : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/40 hover:border-slate-700'
                }`}
              >
                <div
                  className={`p-2.5 rounded-xl flex-shrink-0 ${
                    isSelected
                      ? 'bg-amber-500 text-slate-950'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">
                      {m.title}
                    </span>
                    {isSelected && (
                      <div className="w-5 h-5 rounded-full bg-amber-500 flex items-center justify-center text-slate-950">
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {m.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Big Primary Start Button */}
      <button
        onClick={onStart}
        className="w-full sm:w-auto sm:min-w-[320px] flex items-center justify-center space-x-3 px-8 py-4 rounded-2xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-lg transition-all shadow-xl shadow-amber-500/20 active:scale-[0.98]"
      >
        <Play className="w-6 h-6 fill-slate-950" />
        <span>Start Live {activeMode === 'captions' ? 'Captions' : 'Translation'}</span>
      </button>

      {/* Footer System Specs */}
      <div className="flex items-center space-x-4 mt-6 text-xs text-slate-500">
        <span className="flex items-center space-x-1">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span>{modelProfile.toUpperCase()} ASR (int8)</span>
        </span>
        <span>•</span>
        <span>Sub-500ms Streaming</span>
        <span>•</span>
        <span>Airplane Mode Ready</span>
      </div>
    </div>
  );
};
