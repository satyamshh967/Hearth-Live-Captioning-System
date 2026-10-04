import React from 'react';
import {
  Mic,
  MicOff,
  Flame,
  ShieldCheck,
  Stethoscope,
  QrCode,
  BookOpen,
  Sliders,
  FolderClock,
  Sparkles,
  Languages,
} from 'lucide-react';
import { DeviceRole } from '../types';

interface HeaderProps {
  isListening: boolean;
  onToggleListening: () => void;
  deviceRole: DeviceRole;
  translateMode: boolean;
  onToggleTranslate: () => void;
  plainLanguageMode: boolean;
  onTogglePlainLanguage: () => void;
  onOpenCatchup: () => void;
  onOpenLexicon: () => void;
  onOpenPairing: () => void;
  onOpenSettings: () => void;
  onOpenSessions: () => void;
  onOpenPrivacy: () => void;
  modelProfile: string;
  latencyMs: number;
}

export const Header: React.FC<HeaderProps> = ({
  isListening,
  onToggleListening,
  deviceRole,
  translateMode,
  onToggleTranslate,
  plainLanguageMode,
  onTogglePlainLanguage,
  onOpenCatchup,
  onOpenLexicon,
  onOpenPairing,
  onOpenSettings,
  onOpenSessions,
  onOpenPrivacy,
  modelProfile,
  latencyMs,
}) => {
  return (
    <header className="flex flex-wrap items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800 backdrop-blur z-20">
      {/* Brand & Friend Target */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-500 shadow-inner">
          <Flame className="w-6 h-6 fill-amber-500" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight text-white">Hearth</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-medium">
              for Dadaji
            </span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <span>{modelProfile.toUpperCase()} ASR</span>
            <span>•</span>
            <span>{latencyMs > 0 ? `${latencyMs.toFixed(0)}ms` : 'sub-2s target'}</span>
          </div>
        </div>
      </div>

      {/* Main Center Actions */}
      <div className="flex items-center space-x-2 my-1 sm:my-0">
        {/* Mic toggle */}
        {deviceRole !== 'display' && (
          <button
            onClick={onToggleListening}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl font-semibold text-sm transition-all shadow-md ${
              isListening
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse'
                : 'bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold'
            }`}
          >
            {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            <span>{isListening ? 'Listening...' : 'Start Captions'}</span>
          </button>
        )}

        {/* "What did I miss?" Catch-up button */}
        <button
          onClick={onOpenCatchup}
          className="flex items-center space-x-1.5 px-3 py-2 rounded-xl text-sm font-semibold bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-700/50 text-indigo-200 transition-all shadow"
          title="2-sentence recap of what you missed"
        >
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span className="hidden sm:inline">What did I miss?</span>
          <span className="sm:hidden">Recap</span>
        </button>

        {/* Live Translator to English toggle */}
        <button
          onClick={onToggleTranslate}
          className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all border ${
            translateMode
              ? 'bg-blue-900/80 border-blue-500 text-blue-100 shadow'
              : 'bg-slate-800/80 hover:bg-slate-800 border-slate-700 text-slate-300'
          }`}
          title="Live Speech Translator: Translates multilingual/Hindi speech directly into English captions"
        >
          <Languages className="w-4 h-4 text-blue-400" />
          <span className="hidden md:inline">Live Translate</span>
        </button>

        {/* Doctor Visit / Plain Language toggle */}
        <button
          onClick={onTogglePlainLanguage}
          className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all border ${
            plainLanguageMode
              ? 'bg-teal-900/80 border-teal-500 text-teal-100 shadow'
              : 'bg-slate-800/80 hover:bg-slate-800 border-slate-700 text-slate-300'
          }`}
          title="Translate medical jargon into plain language"
        >
          <Stethoscope className="w-4 h-4 text-teal-400" />
          <span className="hidden md:inline">Plain Language</span>
        </button>
      </div>

      {/* Utility & Accessibility Tools */}
      <div className="flex items-center space-x-1.5">
        {/* Table-Mic QR code */}
        <button
          onClick={onOpenPairing}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition"
          title="Table-Mic Pairing (Phone to Tablet)"
        >
          <QrCode className="w-4 h-4" />
        </button>

        {/* Lexicon */}
        <button
          onClick={onOpenLexicon}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition"
          title="Personal Lexicon (Names, Dishes, Meds)"
        >
          <BookOpen className="w-4 h-4" />
        </button>

        {/* Sessions & Things to Remember */}
        <button
          onClick={onOpenSessions}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition"
          title="Sessions & Memories"
        >
          <FolderClock className="w-4 h-4" />
        </button>

        {/* Settings */}
        <button
          onClick={onOpenSettings}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition"
          title="Display & Font Size Settings"
        >
          <Sliders className="w-4 h-4" />
        </button>

        {/* Local Only Privacy Proof */}
        <button
          onClick={onOpenPrivacy}
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-700/60 text-emerald-300 hover:bg-emerald-900/60 transition text-xs font-semibold"
          title="Local Only - Verified Zero Telemetry"
        >
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="hidden xl:inline">Local Only</span>
        </button>
      </div>
    </header>
  );
};
