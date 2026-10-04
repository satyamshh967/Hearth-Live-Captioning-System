import React from 'react';
import { Sliders, X, Type, Volume2, Smartphone } from 'lucide-react';
import { DeviceRole } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  fontSize: number;
  onChangeFontSize: (size: number) => void;
  fontFamily: 'sans' | 'dyslexic';
  onChangeFontFamily: (family: 'sans' | 'dyslexic') => void;
  lowConfidenceUnderline: boolean;
  onToggleLowConfidence: () => void;
  soundAlerts: boolean;
  onToggleSoundAlerts: () => void;
  hapticAlerts: boolean;
  onToggleHapticAlerts: () => void;
  deviceRole: DeviceRole;
  onChangeDeviceRole: (role: DeviceRole) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  fontSize,
  onChangeFontSize,
  fontFamily,
  onChangeFontFamily,
  lowConfidenceUnderline,
  onToggleLowConfidence,
  soundAlerts,
  onToggleSoundAlerts,
  hapticAlerts,
  onToggleHapticAlerts,
  deviceRole,
  onChangeDeviceRole,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-6">
          <div className="flex items-center space-x-3">
            <div className="p-3 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <Sliders className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Accessibility & Display</h3>
              <p className="text-xs text-slate-400">Tailored for Dadaji's comfort and reading ease</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="space-y-6">
          {/* Font Size Slider */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-bold text-slate-200 flex items-center space-x-2">
                <Type className="w-4 h-4 text-amber-400" />
                <span>Caption Font Size</span>
              </label>
              <span className="text-sm font-mono font-bold text-amber-400">{fontSize}px</span>
            </div>
            <input
              type="range"
              min="18"
              max="46"
              step="2"
              value={fontSize}
              onChange={(e) => onChangeFontSize(Number(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>Standard (18px)</span>
              <span>Table Distance (28px)</span>
              <span>Extra Large (46px)</span>
            </div>
          </div>

          {/* Dyslexia-Friendly Font Toggle */}
          <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700">
            <div>
              <div className="font-bold text-sm text-slate-200">Dyslexia-Friendly Typeface</div>
              <div className="text-xs text-slate-400">Uses Lexend high-legibility glyphs</div>
            </div>
            <button
              onClick={() => onChangeFontFamily(fontFamily === 'sans' ? 'dyslexic' : 'sans')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                fontFamily === 'dyslexic'
                  ? 'bg-amber-500 text-slate-950 font-bold'
                  : 'bg-slate-700 text-slate-300'
              }`}
            >
              {fontFamily === 'dyslexic' ? 'Enabled' : 'Off'}
            </button>
          </div>

          {/* Mark Low Confidence Words */}
          <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700">
            <div>
              <div className="font-bold text-sm text-slate-200">Mark Low-Confidence Words</div>
              <div className="text-xs text-slate-400">Subtle dotted underline on uncertain words</div>
            </div>
            <button
              onClick={onToggleLowConfidence}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                lowConfidenceUnderline
                  ? 'bg-amber-500 text-slate-950 font-bold'
                  : 'bg-slate-700 text-slate-300'
              }`}
            >
              {lowConfidenceUnderline ? 'Enabled' : 'Off'}
            </button>
          </div>

          {/* Audio Chime and Haptic Alert */}
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={onToggleSoundAlerts}
              className={`p-3 rounded-2xl border text-left transition ${
                soundAlerts
                  ? 'bg-indigo-950/50 border-indigo-500/70 text-indigo-200'
                  : 'bg-slate-800/60 border-slate-700 text-slate-400'
              }`}
            >
              <div className="flex items-center space-x-2 font-bold text-sm mb-1">
                <Volume2 className="w-4 h-4 text-indigo-400" />
                <span>Audio Chime</span>
              </div>
              <div className="text-xs text-slate-400">Soft bell on name alerts</div>
            </button>

            <button
              onClick={onToggleHapticAlerts}
              className={`p-3 rounded-2xl border text-left transition ${
                hapticAlerts
                  ? 'bg-amber-950/50 border-amber-500/70 text-amber-200'
                  : 'bg-slate-800/60 border-slate-700 text-slate-400'
              }`}
            >
              <div className="flex items-center space-x-2 font-bold text-sm mb-1">
                <Smartphone className="w-4 h-4 text-amber-400" />
                <span>Haptic Pulse</span>
              </div>
              <div className="text-xs text-slate-400">Vibration API double-pulse</div>
            </button>
          </div>

          {/* Device Role */}
          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Device Operating Mode
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => onChangeDeviceRole('all')}
                className={`py-2 px-3 rounded-xl text-xs font-bold border transition ${
                  deviceRole === 'all'
                    ? 'bg-amber-500 text-slate-950 border-amber-400 font-bold'
                    : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                All-in-One
              </button>
              <button
                onClick={() => onChangeDeviceRole('display')}
                className={`py-2 px-3 rounded-xl text-xs font-bold border transition ${
                  deviceRole === 'display'
                    ? 'bg-amber-500 text-slate-950 border-amber-400 font-bold'
                    : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                Tablet Display
              </button>
              <button
                onClick={() => onChangeDeviceRole('mic')}
                className={`py-2 px-3 rounded-xl text-xs font-bold border transition ${
                  deviceRole === 'mic'
                    ? 'bg-amber-500 text-slate-950 border-amber-400 font-bold'
                    : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                Table Mic Only
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
