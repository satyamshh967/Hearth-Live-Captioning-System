export interface WordItem {
  w: string;
  conf: number;
}

export interface Utterance {
  utt_id: string;
  speaker: string;
  speaker_id?: string;
  text: string;
  plain_text?: string;
  lang: string;
  start: number;
  end: number;
  words?: WordItem[];
  latency_ms?: number;
  is_final: boolean;
  timestamp: number;
  addressed_to_me?: boolean;
  task?: 'transcribe' | 'translate';
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

export type ThemeMode = 'oled-dark' | 'warm-amber' | 'high-contrast-light' | 'midnight-blue';
export type DeviceRole = 'all' | 'display' | 'mic';
