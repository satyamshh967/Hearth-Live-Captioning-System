import React, { useState, useEffect } from 'react';
import { UserCheck, X } from 'lucide-react';

interface SpeakerRenameModalProps {
  isOpen: boolean;
  onClose: () => void;
  speakerId: string;
  currentName: string;
  onSaveRename: (speakerId: string, newName: string) => void;
}

export const SpeakerRenameModal: React.FC<SpeakerRenameModalProps> = ({
  isOpen,
  onClose,
  speakerId,
  currentName,
  onSaveRename,
}) => {
  const [name, setName] = useState('');

  useEffect(() => {
    setName(currentName);
  }, [currentName]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onSaveRename(speakerId, name.trim());
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 max-w-sm w-full shadow-2xl relative">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-2 text-indigo-400 font-bold">
            <UserCheck className="w-5 h-5" />
            <h3 className="text-lg text-white">Rename Speaker</h3>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Speaker ID
            </label>
            <div className="text-xs text-slate-500 font-mono mb-2">
              {speakerId}
            </div>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Priya, Rohan, Dadaji"
              className="w-full p-3 rounded-xl bg-slate-800 border-2 border-indigo-500/60 focus:border-indigo-400 text-white text-base font-bold outline-none"
              autoFocus
            />
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
              disabled={!name.trim()}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-sm shadow transition"
            >
              Save Name
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
