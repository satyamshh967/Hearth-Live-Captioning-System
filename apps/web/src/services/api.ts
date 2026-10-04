import { LexiconItem, MemoryItem } from '../types';

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch(`${API_BASE}/config`);
  return res.json();
}

export async function fetchLexicon(): Promise<{ items: LexiconItem[]; prompt_biasing_string: string }> {
  const res = await fetch(`${API_BASE}/lexicon`);
  return res.json();
}

export async function addLexiconWord(word: string, category: string = 'custom'): Promise<LexiconItem> {
  const res = await fetch(`${API_BASE}/lexicon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ word, category }),
  });
  return res.json();
}

export async function deleteLexiconWord(word: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/lexicon/${encodeURIComponent(word)}`, {
    method: 'DELETE',
  });
  const data = await res.json();
  return data.success;
}

export async function recordCorrection(original: string, corrected: string, context?: string) {
  const res = await fetch(`${API_BASE}/corrections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ original, corrected, context }),
  });
  return res.json();
}

export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  return res.json();
}

export async function fetchSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  return res.json();
}

export async function createSession(title: string) {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function addSessionMemory(sessionId: string, memory: MemoryItem) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/memories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(memory),
  });
  return res.json();
}

export async function toggleMemoryConfirmed(memoryId: number) {
  const res = await fetch(`${API_BASE}/memories/${memoryId}/toggle`, {
    method: 'POST',
  });
  return res.json();
}

export async function renameSpeakerApi(speakerId: string, newName: string) {
  const res = await fetch(`${API_BASE}/speakers/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speaker_id: speakerId, new_name: newName }),
  });
  return res.json();
}

export async function simplifyPlainLanguageApi(text: string) {
  const res = await fetch(`${API_BASE}/plain_language`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return res.json();
}

export async function deleteAllDataApi() {
  const res = await fetch(`${API_BASE}/privacy/delete-all`, {
    method: 'POST',
  });
  return res.json();
}

export async function verifyOfflineApi() {
  const res = await fetch(`${API_BASE}/privacy/verify-offline`);
  return res.json();
}
