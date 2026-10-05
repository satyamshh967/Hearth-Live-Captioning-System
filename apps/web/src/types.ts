export type AppMode = 'captions' | 'listening' | 'conversation' | 'text_only' | 'custom';

export interface WordItem {
  w: string;
  conf: number;
}

export interface Utterance {
  utt_id: string;
  speaker: string;
  speaker_id?: string;
  text: string;
  translated_text?: string;
  plain_text?: string;
  lang: string;
  source_lang?: string;
  target_lang?: string;
  start: number;
  end: number;
  words?: WordItem[];
  latency_ms?: number;
  is_final: boolean;
  timestamp: number;
  addressed_to_me?: boolean;
  task?: 'transcribe' | 'translate';
  mode?: AppMode;
  t_capture?: number;
  latency_breakdown?: Record<string, number>;
}

export interface StreamingState {
  utt_id: string;
  committed_source: string;
  tentative_source: string;
  committed_translated: string;
  tentative_translated: string;
  speaker: string;
  source_lang: string;
  target_lang: string;
  mode: AppMode;
  t_capture: number;
  latency_breakdown?: Record<string, number>;
}

export interface QuickReply {
  label: string;
  text: string;
}

export interface MemoryItem {
  id?: number;
  category: string;
  title: string;
  detail: string;
  time_or_date?: string;
  confirmed?: boolean;
}

export interface LexiconItem {
  id: number;
  word: string;
  phonetic: string;
  category: string;
  frequency: number;
  user_confirmed: number;
}

export interface ProfileItem {
  id: string;
  name: string;
  description: string;
  vocab_count: number;
  is_active: boolean;
}

export interface LanguagePack {
  id: string;
  name: string;
  version: string;
  description: string;
  languages: string[];
  size_mb: number;
  license: string;
  tts_voice: string;
  is_installed: boolean;
}

export type ThemeMode = 'midnight-blue' | 'high-contrast-light' | 'oled-dark' | 'warm-amber';
export type DeviceRole = 'all' | 'display' | 'mic';
