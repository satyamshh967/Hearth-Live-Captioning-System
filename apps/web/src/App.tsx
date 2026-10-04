import React, { useState, useEffect, useRef } from 'react';
import {
  Utterance,
  QuickReply,
  LexiconItem,
  DeviceRole,
} from './types';
import { Header } from './components/Header';
import { CaptionStream } from './components/CaptionStream';
import { AddressedAlertBanner } from './components/AddressedAlertBanner';
import { QuickRepliesDrawer } from './components/QuickRepliesDrawer';
import { CatchupModal } from './components/CatchupModal';
import { WordCorrectionModal } from './components/WordCorrectionModal';
import { TableMicModal } from './components/TableMicModal';
import { LexiconModal } from './components/LexiconModal';
import { SessionHistoryModal } from './components/SessionHistoryModal';
import { SettingsModal } from './components/SettingsModal';
import { PrivacyModal } from './components/PrivacyModal';
import { SpeakerRenameModal } from './components/SpeakerRenameModal';

import { audioCapture } from './services/audio';
import { playGentleChime, triggerHaptic } from './services/chime';
import {
  fetchHealth,
  fetchLexicon,
  addLexiconWord,
  deleteLexiconWord,
  recordCorrection,
  renameSpeakerApi,
  simplifyPlainLanguageApi,
} from './services/api';

export const App: React.FC = () => {
  // Query parameters for table-mic pairing
  const queryParams = new URLSearchParams(window.location.search);
  const initialRoom = queryParams.get('room') || 'TABLE-4821';
  const initialRole = (queryParams.get('role') as DeviceRole) || 'all';

  // Core Real-Time State
  const [isListening, setIsListening] = useState(false);
  const [utterances, setUtterances] = useState<Utterance[]>([]);
  const [partialText, setPartialText] = useState('');
  const [roomId] = useState(initialRoom);
  const [deviceRole, setDeviceRole] = useState<DeviceRole>(initialRole);
  const [modelProfile, setModelProfile] = useState('balanced');
  const [latencyMs, setLatencyMs] = useState(0);

  // Intelligence State
  const [activeAlert, setActiveAlert] = useState<{ vocative: string; utt_id: string } | null>(null);
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([]);
  const [plainLanguageMode, setPlainLanguageMode] = useState(false);

  // Modals & Drawers
  const [isCatchupOpen, setIsCatchupOpen] = useState(false);
  const [catchupRecap, setCatchupRecap] = useState({ text: '', topic: '', speakers: [] as string[] });
  const [isCatchupLoading, setIsCatchupLoading] = useState(false);

  const [isCorrectionOpen, setIsCorrectionOpen] = useState(false);
  const [correctionTarget, setCorrectionTarget] = useState({ word: '', context: '' });

  const [isPairingOpen, setIsPairingOpen] = useState(false);
  const [isLexiconOpen, setIsLexiconOpen] = useState(false);
  const [isSessionsOpen, setIsSessionsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);

  const [renameTarget, setRenameTarget] = useState<{ id: string; name: string } | null>(null);

  // Accessibility Settings
  const [fontSize, setFontSize] = useState<number>(() => {
    return Number(localStorage.getItem('hearth_font_size')) || 28;
  });
  const [fontFamily, setFontFamily] = useState<'sans' | 'dyslexic'>(() => {
    return (localStorage.getItem('hearth_font_family') as any) || 'sans';
  });
  const [lowConfidenceUnderline, setLowConfidenceUnderline] = useState(true);
  const [soundAlerts, setSoundAlerts] = useState(true);
  const [hapticAlerts, setHapticAlerts] = useState(true);

  // Lexicon items
  const [lexiconItems, setLexiconItems] = useState<LexiconItem[]>([]);

  // WebSocket Ref
  const wsRef = useRef<WebSocket | null>(null);

  // Sync settings to localStorage
  useEffect(() => {
    localStorage.setItem('hearth_font_size', String(fontSize));
  }, [fontSize]);

  useEffect(() => {
    localStorage.setItem('hearth_font_family', fontFamily);
  }, [fontFamily]);

  // Load initial health & lexicon
  useEffect(() => {
    fetchHealth()
      .then((data) => {
        if (data.profile) setModelProfile(data.profile);
      })
      .catch((err) => console.debug('Health fetch failed:', err));

    loadLexicon();
  }, []);

  const loadLexicon = async () => {
    try {
      const data = await fetchLexicon();
      setLexiconItems(data.items || []);
    } catch (e) {
      console.debug('Failed to load lexicon:', e);
    }
  };

  // Connect WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws?room=${encodeURIComponent(roomId)}&role=${encodeURIComponent(deviceRole)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to Hearth WebSocket server:', wsUrl);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleServerMessage(msg);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed.');
    };

    return () => {
      ws.close();
    };
  }, [roomId, deviceRole]);

  // Handle incoming server messages
  const handleServerMessage = (msg: any) => {
    if (msg.type === 'status') {
      if (msg.latency_ms) setLatencyMs(msg.latency_ms);
      if (msg.profile) setModelProfile(msg.profile);
    } else if (msg.type === 'partial') {
      setPartialText(msg.text || '');
    } else if (msg.type === 'final') {
      setPartialText('');
      const newUtt: Utterance = {
        utt_id: msg.utt_id,
        speaker: msg.speaker || 'Speaker',
        speaker_id: msg.speaker_id,
        text: msg.text,
        lang: msg.lang || 'en',
        start: msg.start || 0,
        end: msg.end || 0,
        words: msg.words || [],
        latency_ms: msg.latency_ms,
        is_final: true,
        timestamp: Date.now(),
      };
      setUtterances((prev) => [...prev, newUtt]);
      if (msg.latency_ms) setLatencyMs(msg.latency_ms);
    } else if (msg.type === 'alert') {
      if (msg.kind === 'name') {
        const vocative = msg.vocative || 'Dadaji';
        setActiveAlert({ vocative, utt_id: msg.utt_id });
        if (soundAlerts) playGentleChime();
        if (hapticAlerts) triggerHaptic();

        // Mark utterance as addressed to user
        setUtterances((prev) =>
          prev.map((u) => (u.utt_id === msg.utt_id ? { ...u, addressed_to_me: true } : u))
        );
      }
    } else if (msg.type === 'suggestions') {
      if (msg.replies && msg.replies.length > 0) {
        setQuickReplies(msg.replies);
      }
    } else if (msg.type === 'recap') {
      setCatchupRecap({
        text: msg.text,
        topic: msg.topic || 'General conversation',
        speakers: msg.speakers || [],
      });
      setIsCatchupLoading(false);
    } else if (msg.type === 'plain_language') {
      setUtterances((prev) =>
        prev.map((u) => (u.utt_id === msg.utt_id ? { ...u, plain_text: msg.plain_text } : u))
      );
    }
  };

  // Toggle mic listening
  const handleToggleListening = async () => {
    if (isListening) {
      audioCapture.stop();
      setIsListening(false);
    } else {
      try {
        await audioCapture.start((buffer) => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(buffer);
          }
        });
        setIsListening(true);
      } catch (err) {
        alert('Microphone permission required to transcribe audio.');
      }
    }
  };

  // "What did I miss?" Catchup
  const handleOpenCatchup = () => {
    setIsCatchupOpen(true);
    setIsCatchupLoading(true);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'catchup' }));
    }
  };

  // Word correction
  const handleCorrectWord = (word: string, context: string) => {
    setCorrectionTarget({ word, context });
    setIsCorrectionOpen(true);
  };

  const handleSaveCorrection = async (original: string, corrected: string, context: string) => {
    try {
      await recordCorrection(original, corrected, context);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'correct_word',
            original,
            corrected,
            context,
          })
        );
      }
      loadLexicon();

      // Update in active stream
      setUtterances((prev) =>
        prev.map((u) => {
          if (u.text.includes(original)) {
            const updatedText = u.text.replace(new RegExp(original, 'gi'), corrected);
            return {
              ...u,
              text: updatedText,
              words: u.words?.map((w) =>
                w.w.toLowerCase() === original.toLowerCase() ? { ...w, w: corrected } : w
              ),
            };
          }
          return u;
        })
      );
    } catch (e) {
      console.error(e);
    }
  };

  // Speaker rename
  const handleRenameSpeaker = (speakerId: string, currentName: string) => {
    setRenameTarget({ id: speakerId, name: currentName });
  };

  const handleSaveSpeakerRename = async (speakerId: string, newName: string) => {
    try {
      await renameSpeakerApi(speakerId, newName);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'rename_speaker',
            speaker_id: speakerId,
            new_name: newName,
          })
        );
      }
      // Update utterances
      setUtterances((prev) =>
        prev.map((u) => (u.speaker === renameTarget?.name ? { ...u, speaker: newName } : u))
      );
    } catch (e) {
      console.error(e);
    }
  };

  // Lexicon CRUD
  const handleAddLexiconWord = async (word: string, category: string) => {
    await addLexiconWord(word, category);
    loadLexicon();
  };

  const handleDeleteLexiconWord = async (word: string) => {
    await deleteLexiconWord(word);
    loadLexicon();
  };

  // Plain language request
  const handleRequestPlainLanguage = async (uttId: string, text: string) => {
    try {
      const res = await simplifyPlainLanguageApi(text);
      setUtterances((prev) =>
        prev.map((u) => (u.utt_id === uttId ? { ...u, plain_text: res.plain_text } : u))
      );
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div
      className={`h-screen w-screen flex flex-col bg-slate-950 text-slate-100 ${
        activeAlert ? 'alert-pulse-amber' : ''
      }`}
    >
      {/* Top Header */}
      <Header
        isListening={isListening}
        onToggleListening={handleToggleListening}
        deviceRole={deviceRole}
        plainLanguageMode={plainLanguageMode}
        onTogglePlainLanguage={() => setPlainLanguageMode((prev) => !prev)}
        onOpenCatchup={handleOpenCatchup}
        onOpenLexicon={() => setIsLexiconOpen(true)}
        onOpenPairing={() => setIsPairingOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenSessions={() => setIsSessionsOpen(true)}
        onOpenPrivacy={() => setIsPrivacyOpen(true)}
        modelProfile={modelProfile}
        latencyMs={latencyMs}
      />

      {/* Addressed-to-Me Notification Banner */}
      {activeAlert && (
        <AddressedAlertBanner
          vocative={activeAlert.vocative}
          onDismiss={() => setActiveAlert(null)}
        />
      )}

      {/* Main Live Caption Stream */}
      <CaptionStream
        utterances={utterances}
        partialText={partialText}
        fontSize={fontSize}
        fontFamily={fontFamily}
        lowConfidenceUnderline={lowConfidenceUnderline}
        plainLanguageMode={plainLanguageMode}
        onCorrectWord={handleCorrectWord}
        onRenameSpeaker={handleRenameSpeaker}
        onRequestPlainLanguage={handleRequestPlainLanguage}
      />

      {/* Quick Replies Drawer */}
      {quickReplies.length > 0 && (
        <QuickRepliesDrawer
          replies={quickReplies}
          onDismiss={() => setQuickReplies([])}
        />
      )}

      {/* Modals */}
      <CatchupModal
        isOpen={isCatchupOpen}
        onClose={() => setIsCatchupOpen(false)}
        recapText={catchupRecap.text}
        topic={catchupRecap.topic}
        speakers={catchupRecap.speakers}
        isLoading={isCatchupLoading}
        onRefresh={handleOpenCatchup}
      />

      <WordCorrectionModal
        isOpen={isCorrectionOpen}
        onClose={() => setIsCorrectionOpen(false)}
        originalWord={correctionTarget.word}
        context={correctionTarget.context}
        onSaveCorrection={handleSaveCorrection}
      />

      <TableMicModal
        isOpen={isPairingOpen}
        onClose={() => setIsPairingOpen(false)}
        roomId={roomId}
      />

      <LexiconModal
        isOpen={isLexiconOpen}
        onClose={() => setIsLexiconOpen(false)}
        items={lexiconItems}
        onAddWord={handleAddLexiconWord}
        onDeleteWord={handleDeleteLexiconWord}
      />

      <SessionHistoryModal
        isOpen={isSessionsOpen}
        onClose={() => setIsSessionsOpen(false)}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        fontSize={fontSize}
        onChangeFontSize={setFontSize}
        fontFamily={fontFamily}
        onChangeFontFamily={setFontFamily}
        lowConfidenceUnderline={lowConfidenceUnderline}
        onToggleLowConfidence={() => setLowConfidenceUnderline((prev) => !prev)}
        soundAlerts={soundAlerts}
        onToggleSoundAlerts={() => setSoundAlerts((prev) => !prev)}
        hapticAlerts={hapticAlerts}
        onToggleHapticAlerts={() => setHapticAlerts((prev) => !prev)}
        deviceRole={deviceRole}
        onChangeDeviceRole={setDeviceRole}
      />

      <PrivacyModal
        isOpen={isPrivacyOpen}
        onClose={() => setIsPrivacyOpen(false)}
        onDataDeleted={() => setUtterances([])}
      />

      {renameTarget && (
        <SpeakerRenameModal
          isOpen={true}
          onClose={() => setRenameTarget(null)}
          speakerId={renameTarget.id}
          currentName={renameTarget.name}
          onSaveRename={handleSaveSpeakerRename}
        />
      )}
    </div>
  );
};

export default App;
