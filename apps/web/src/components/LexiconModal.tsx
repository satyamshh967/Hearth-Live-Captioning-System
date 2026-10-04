import React, { useState } from 'react';
import { LexiconItem } from '../types';
import { BookOpen, Plus, Trash2, X, Search } from 'lucide-react';

interface LexiconModalProps {
  isOpen: boolean;
  onClose: () => void;
  items: LexiconItem[];
  onAddWord: (word: string, category: string) => void;
  onDeleteWord: (word: string) => void;
}

export const LexiconModal: React.FC<LexiconModalProps> = ({
  isOpen,
  onClose,
  items,
  onAddWord,
  onDeleteWord,
}) => {
  const [search, setSearch] = useState('');
  const [newWord, setNewWord] = useState('');
  const [newCategory, setNewCategory] = useState('family');

  if (!isOpen) return null;

  const filtered = items.filter((item) =>
    item.word.toLowerCase().includes(search.toLowerCase()) ||
    item.category.toLowerCase().includes(search.toLowerCase())
  );

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (newWord.trim()) {
      onAddWord(newWord.trim(), newCategory);
      setNewWord('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 sm:p-8 max-w-2xl w-full shadow-2xl relative max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-3 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Personal Lexicon</h3>
              <p className="text-xs text-slate-400">
                {items.length} words biasing Whisper ASR & phonetically corrected
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Add new word form */}
        <form onSubmit={handleAdd} className="flex flex-wrap gap-2 mb-4 p-3 rounded-2xl bg-slate-800/60 border border-slate-700">
          <input
            type="text"
            value={newWord}
            onChange={(e) => setNewWord(e.target.value)}
            placeholder="Add name, dish, medicine, or word..."
            className="flex-1 min-w-[180px] px-3 py-2 rounded-xl bg-slate-800 border border-slate-600 text-white text-sm focus:border-amber-400 outline-none"
          />
          <select
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-600 text-slate-300 text-sm outline-none"
          >
            <option value="family">Family / Kinship</option>
            <option value="food">Dish / Food</option>
            <option value="medicine">Medicine / Health</option>
            <option value="phrase">Phrase / Hindi</option>
            <option value="custom">Custom</option>
          </select>
          <button
            type="submit"
            disabled={!newWord.trim()}
            className="flex items-center space-x-1 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-sm shadow transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add</span>
          </button>
        </form>

        {/* Search */}
        <div className="relative mb-3">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter lexicon..."
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-800/40 border border-slate-700 text-slate-200 text-sm outline-none"
          />
        </div>

        {/* Word list */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              No matching words in lexicon.
            </div>
          ) : (
            filtered.map((item) => (
              <div
                key={item.id || item.word}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-850 hover:bg-slate-800/80 border border-slate-800 transition"
              >
                <div className="flex items-center space-x-3">
                  <span className="font-bold text-slate-100 text-base">{item.word}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 uppercase">
                    {item.category}
                  </span>
                  {item.phonetic && (
                    <span className="text-xs font-mono text-slate-400" title="Soundex code">
                      [{item.phonetic}]
                    </span>
                  )}
                </div>
                <button
                  onClick={() => onDeleteWord(item.word)}
                  className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition"
                  title="Remove word from lexicon"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
