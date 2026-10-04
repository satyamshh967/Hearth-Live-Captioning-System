import React, { useState, useEffect } from 'react';
import { Check, X, BookOpen } from 'lucide-react';

interface WordCorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  originalWord: string;
  context: string;
  onSaveCorrection: (original: string, corrected: string, context: string) => void;
}

export const WordCorrectionModal: React.FC<WordCorrectionModalProps> = ({
  isOpen,
  onClose,
  originalWord,
  context,
  onSaveCorrection,
}) => {
  const [correctedWord, setCorrectedWord] = useState('');

  useEffect(() => {
    setCorrectedWord(originalWord);
  }, [originalWord]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (correctedWord.trim() && correctedWord.trim() !== originalWord) {
      onSaveCorrection(originalWord, correctedWord.trim(), context);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl relative">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-2 text-amber-400 font-bold">
            <BookOpen className="w-5 h-5" />
            <h3 className="text-lg text-white">Correct-to-Learn Loop</h3>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-400 mb-4">
          Fixing this misheard word adds it to your personal lexicon and trains Hearth to recognize it correctly next time.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Misheard Word
            </label>
            <div className="p-3 rounded-xl bg-slate-800 text-slate-300 font-mono text-base border border-slate-700">
              "{originalWord}"
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-amber-400 mb-1">
              Correct Word / Name
            </label>
            <input
              type="text"
              value={correctedWord}
              onChange={(e) => setCorrectedWord(e.target.value)}
              className="w-full p-3 rounded-xl bg-slate-800 border-2 border-amber-500/60 focus:border-amber-400 text-white text-lg font-bold outline-none transition"
              autoFocus
              placeholder="e.g. Dadaji, Metformin, Dal makhani"
            />
          </div>

          <div className="text-xs text-slate-500 italic truncate">
            Context: "{context}"
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-sm font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!correctedWord.trim() || correctedWord.trim() === originalWord}
              className="flex items-center space-x-1.5 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-sm shadow transition"
            >
              <Check className="w-4 h-4" />
              <span>Save & Teach Hearth</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
