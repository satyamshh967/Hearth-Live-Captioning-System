import React, { useState, useEffect } from 'react';
import {
  FolderClock,
  Calendar,
  CheckCircle2,
  Circle,
  X,
  FileText,
  Subtitles,
  Download,
} from 'lucide-react';
import { fetchSessions, fetchSession, toggleMemoryConfirmed } from '../services/api';

interface SessionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SessionHistoryModal: React.FC<SessionHistoryModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen]);

  const loadSessions = async () => {
    try {
      const data = await fetchSessions();
      setSessions(data || []);
      if (data && data.length > 0 && !selectedSession) {
        loadSessionDetails(data[0].session_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadSessionDetails = async (sessionId: string) => {
    try {
      const sess = await fetchSession(sessionId);
      setSelectedSession(sess);
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleMemory = async (memId: number) => {
    try {
      const res = await toggleMemoryConfirmed(memId);
      if (selectedSession && selectedSession.memories) {
        setSelectedSession({
          ...selectedSession,
          memories: selectedSession.memories.map((m: any) =>
            m.id === memId ? { ...m, confirmed: res.confirmed ? 1 : 0 } : m
          ),
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 sm:p-8 max-w-4xl w-full shadow-2xl relative max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-3 rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <FolderClock className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Session Library & Memory Chips</h3>
              <p className="text-xs text-slate-400">
                Search transcripts, confirmed medicines/tasks, and export to Markdown or ICS
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* 2-column layout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 overflow-hidden">
          {/* Left: Sessions List */}
          <div className="border-r border-slate-800 pr-4 flex flex-col space-y-2 overflow-y-auto">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
              Recorded Sessions
            </div>
            {sessions.length === 0 ? (
              <div className="text-slate-500 text-sm py-4">No past sessions found.</div>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.session_id}
                  onClick={() => loadSessionDetails(s.session_id)}
                  className={`text-left p-3 rounded-2xl transition border ${
                    selectedSession?.session_id === s.session_id
                      ? 'bg-indigo-950/60 border-indigo-500/60 text-white'
                      : 'bg-slate-850 hover:bg-slate-800 border-slate-800 text-slate-300'
                  }`}
                >
                  <div className="font-bold text-sm truncate">{s.title || 'Family Table'}</div>
                  <div className="text-xs text-slate-500 flex justify-between mt-1">
                    <span>{new Date(s.created_at).toLocaleDateString()}</span>
                    <span>{s.utterance_count || 0} captions</span>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Right: Selected Session Details */}
          <div className="md:col-span-2 flex flex-col overflow-y-auto space-y-4 pr-1">
            {selectedSession ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
                  <div>
                    <h4 className="text-lg font-bold text-white">{selectedSession.title}</h4>
                    <span className="text-xs text-slate-400">
                      Recorded on {new Date(selectedSession.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <a
                      href={`/api/sessions/${selectedSession.session_id}/export/markdown`}
                      download={`hearth_${selectedSession.session_id}.md`}
                      className="flex items-center space-x-1 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
                      title="Download Markdown Transcript"
                    >
                      <FileText className="w-3.5 h-3.5 text-amber-400" />
                      <span>MD</span>
                    </a>
                    <a
                      href={`/api/sessions/${selectedSession.session_id}/export/srt`}
                      download={`hearth_${selectedSession.session_id}.srt`}
                      className="flex items-center space-x-1 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
                      title="Download SubRip Subtitles (.SRT) with source and translations"
                    >
                      <Subtitles className="w-3.5 h-3.5 text-cyan-400" />
                      <span>SRT</span>
                    </a>
                    <a
                      href={`/api/sessions/${selectedSession.session_id}/export/vtt`}
                      download={`hearth_${selectedSession.session_id}.vtt`}
                      className="flex items-center space-x-1 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
                      title="Download WebVTT Captions (.VTT)"
                    >
                      <Download className="w-3.5 h-3.5 text-emerald-400" />
                      <span>VTT</span>
                    </a>
                    <a
                      href={`/api/sessions/${selectedSession.session_id}/export/ics`}
                      download={`hearth_${selectedSession.session_id}.ics`}
                      className="flex items-center space-x-1 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
                      title="Add extracted reminders to Calendar (.ICS)"
                    >
                      <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                      <span>ICS</span>
                    </a>
                  </div>
                </div>

                {/* "Things to remember" chips */}
                <div>
                  <h5 className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2">
                    Things to Remember (Medicines, Plans & Appointments)
                  </h5>
                  {selectedSession.memories && selectedSession.memories.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {selectedSession.memories.map((m: any) => (
                        <div
                          key={m.id}
                          onClick={() => handleToggleMemory(m.id)}
                          className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-2.5 ${
                            m.confirmed
                              ? 'bg-emerald-950/40 border-emerald-700/60 text-slate-200'
                              : 'bg-slate-800/60 border-slate-700 text-slate-300 hover:border-slate-600'
                          }`}
                        >
                          {m.confirmed ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                          ) : (
                            <Circle className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1">
                            <div className="font-bold text-sm leading-tight text-white">{m.title}</div>
                            <div className="text-xs text-slate-400 mt-0.5">{m.detail}</div>
                            {m.time_or_date && (
                              <div className="text-xs text-amber-400/90 font-medium mt-1">
                                {m.time_or_date}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500 italic p-3 rounded-xl bg-slate-800/30">
                      No explicit medicines or appointments detected in this session yet.
                    </div>
                  )}
                </div>

                {/* Utterance preview */}
                <div className="flex-1">
                  <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                    Transcript History ({selectedSession.utterances?.length || 0})
                  </h5>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedSession.utterances && selectedSession.utterances.length > 0 ? (
                      selectedSession.utterances.map((u: any, idx: number) => (
                        <div key={idx} className="p-2.5 rounded-xl bg-slate-850 text-sm border border-slate-800">
                          <div className="flex items-center justify-between text-xs mb-0.5">
                            <strong className="text-amber-400 font-semibold">{u.speaker}</strong>
                            {u.start_sec !== undefined && (
                              <span className="text-[11px] font-mono text-slate-500">
                                {Number(u.start_sec).toFixed(1)}s - {u.end_sec ? Number(u.end_sec).toFixed(1) : ''}s
                              </span>
                            )}
                          </div>
                          <div className="text-slate-200">{u.text}</div>
                          {u.translation && (
                            <div className="text-cyan-400 text-xs mt-1 border-l-2 border-cyan-500/40 pl-2 italic">
                              {u.translation}
                            </div>
                          )}
                          {u.plain_text && (
                            <div className="text-indigo-400 text-xs mt-1 border-l-2 border-indigo-500/40 pl-2">
                              Simple: {u.plain_text}
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-500 text-xs py-2">No utterances recorded.</div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">
                Select a session to view details.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
