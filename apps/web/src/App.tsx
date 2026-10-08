import React, { useState, useEffect, useRef } from 'react';
import {
  Utterance,
  QuickReply,
  LexiconItem,
  DeviceRole,
  AppMode,
  StreamingState,
} from './types';
import { Header } from './components/Header';
import { CaptionStream } from './components/CaptionStream';
import { ConversationView } from './components/ConversationView';
import { HomeScreen } from './components/HomeScreen';
import { ModeSelectorSheet } from './components/ModeSelectorSheet';
import { DebugHud } from './components/DebugHud';
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
  const initialRoom = queryParams.get('room') || 'TABLE-1001';
  const initialRole = (queryParams.get('role') as DeviceRole) || 'all';

  // Core Real-Time State
  const [isListening, setIsListening] = useState(false);
  const [utterances, setUtterances] = useState<Utterance[]>([]);
  const [streamingState, setStreamingState] = useState<StreamingState | null>(null);
  const [roomId] = useState(initialRoom);
  const [deviceRole, setDeviceRole] = useState<DeviceRole>(initialRole);
  const [modelProfile, setModelProfile] = useState('balanced');
  const [latencyMs, setLatencyMs] = useState(0);
  const [totalSpokenToDisplayMs, setTotalSpokenToDisplayMs] = useState(0);
  const [activeProfileName, setActiveProfileName] = useState('Default (General)');

  // Mode and Language Selection
  const [activeMode, setActiveMode] = useState<AppMode>('captions');
  const [sourceLang, setSourceLang] = useState<string>('auto');
  const [targetLang, setTargetLang] = useState<string>('en');
  const [isModeSheetOpen, setIsModeSheetOpen] = useState(false);
  const [isDebugHudOpen, setIsDebugHudOpen] = useState(false);
  const [hasStartedSession, setHasStartedSession] = useState(false);

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
  const speechRecRef = useRef<any>(null);

  // Keyboard Shortcuts: Ctrl+Shift+L for Debug HUD, Space for mic start/stop
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'L' || e.key === 'l')) {
        e.preventDefault();
        setIsDebugHudOpen((prev) => !prev);
      } else if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        handleToggleListening();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isListening]);

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
        if (data.mode) setActiveMode(data.mode);
        if (data.active_profile) setActiveProfileName(data.active_profile);
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
    const renderTime = Date.now() / 1000.0;

    if (msg.type === 'status') {
      if (msg.latency_ms) setLatencyMs(msg.latency_ms);
      if (msg.profile) setModelProfile(msg.profile);
      if (msg.mode) setActiveMode(msg.mode);
      if (msg.active_profile) setActiveProfileName(msg.active_profile);

    } else if (msg.type === 'streaming_update') {
      // Live streaming update with solid committed words + tentative mutable tail
      setStreamingState({
        utt_id: msg.utt_id,
        committed_source: msg.committed_source || '',
        tentative_source: msg.tentative_source || '',
        committed_translated: msg.committed_translated || '',
        tentative_translated: msg.tentative_translated || '',
        speaker: msg.speaker || 'Speaker',
        source_lang: msg.source_lang || 'en',
        target_lang: msg.target_lang || 'en',
        mode: msg.mode || activeMode,
        t_capture: msg.t_capture || renderTime,
        latency_breakdown: msg.latency_breakdown,
      });

      // Compute true spoken -> displayed latency
      if (msg.t_capture) {
        const trueLatency = (renderTime - msg.t_capture) * 1000;
        setTotalSpokenToDisplayMs(trueLatency);
      }

    } else if (msg.type === 'partial') {
      setStreamingState((prev) => {
        if (!prev) {
          return {
            utt_id: msg.utt_id || 'stream',
            committed_source: '',
            tentative_source: msg.text || '',
            committed_translated: '',
            tentative_translated: '',
            speaker: 'Speaker',
            source_lang: sourceLang,
            target_lang: targetLang,
            mode: activeMode,
            t_capture: msg.t_capture || renderTime,
          };
        }
        return prev;
      });

    } else if (msg.type === 'final') {
      // Utterance finalized at silence endpoint
      setStreamingState(null);

      const newUtt: Utterance = {
        utt_id: msg.utt_id,
        speaker: msg.speaker || 'Speaker',
        speaker_id: msg.speaker_id,
        text: msg.text,
        translated_text: msg.translated_text || '',
        lang: msg.lang || 'en',
        source_lang: sourceLang,
        target_lang: targetLang,
        task: msg.task,
        start: msg.start || 0,
        end: msg.end || 0,
        words: msg.words || [],
        latency_ms: msg.latency_ms,
        is_final: true,
        timestamp: Date.now(),
        t_capture: msg.t_capture,
        latency_breakdown: msg.latency_breakdown,
      };

      setUtterances((prev) => [...prev, newUtt]);
      if (msg.latency_ms) setLatencyMs(msg.latency_ms);

      if (msg.t_capture) {
        const trueLatency = (renderTime - msg.t_capture) * 1000;
        setTotalSpokenToDisplayMs(trueLatency);
      }

      // Auto speech output if in Listening mode and user desires voice
      if (activeMode === 'listening' && msg.translated_text) {
        handleSpeakText(msg.translated_text, targetLang);
      }

    } else if (msg.type === 'alert') {
      if (msg.kind === 'name') {
        const vocative = msg.vocative || 'Notice';
        setActiveAlert({ vocative, utt_id: msg.utt_id });
        if (soundAlerts) playGentleChime();
        if (hapticAlerts) triggerHaptic();

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
      if (speechRecRef.current) {
        try {
          speechRecRef.current.stop();
        } catch (_) {}
        speechRecRef.current = null;
      }
      audioCapture.stop();
      setIsListening(false);
    } else {
      try {
        setHasStartedSession(true);

        // Instant client-side speech recognition for true zero-delay visual captions
        const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRec) {
          try {
            const sr = new SpeechRec();
            sr.continuous = true;
            sr.interimResults = true;
            sr.lang = sourceLang === 'auto' ? 'en-US' : sourceLang;
            sr.onresult = (e: any) => {
              let interimText = '';
              for (let i = e.resultIndex; i < e.results.length; ++i) {
                if (!e.results[i].isFinal) {
                  interimText += e.results[i][0].transcript;
                }
              }
              if (interimText.trim()) {
                setStreamingState((prev) => ({
                  utt_id: prev?.utt_id || 'live-instant',
                  committed_source: prev?.committed_source || '',
                  tentative_source: interimText,
                  committed_translated: prev?.committed_translated || '',
                  tentative_translated: prev?.tentative_translated || '',
                  speaker: prev?.speaker || 'You',
                  source_lang: sourceLang,
                  target_lang: targetLang,
                  mode: activeMode,
                  t_capture: Date.now() / 1000,
                }));
              }
            };
            sr.onerror = () => {};
            sr.start();
            speechRecRef.current = sr;
          } catch (srErr) {
            console.debug('Client WebSpeech engine init:', srErr);
          }
        }

        await audioCapture.start((buffer) => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(buffer);
          }
        });
        setIsListening(true);
      } catch (err) {
        alert('Microphone permission required to capture audio.');
      }
    }
  };

  // Mode switching
  const handleSelectMode = (mode: AppMode) => {
    setActiveMode(mode);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'set_mode', mode }));
    }
  };

  // Language pair switching
  const handleSelectSourceLang = (lang: string) => {
    setSourceLang(lang);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: 'set_language_pair', source_lang: lang, target_lang: targetLang })
      );
    }
  };

  const handleSelectTargetLang = (lang: string) => {
    setTargetLang(lang);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: 'set_language_pair', source_lang: sourceLang, target_lang: lang })
      );
    }
  };

  const handleSwapLanguages = () => {
    if (sourceLang === 'auto') return;
    const oldSrc = sourceLang;
    const oldTgt = targetLang;
    setSourceLang(oldTgt);
    setTargetLang(oldSrc);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: 'set_language_pair', source_lang: oldTgt, target_lang: oldSrc })
      );
    }
  };

  // Offline speech synthesis
  const handleSpeakText = (text: string, lang: string) => {
    if ('speechSynthesis' in window && text) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Lexicon Actions
  const handleAddLexiconWord = async (word: string, category: string) => {
    await addLexiconWord(word, category);
    await loadLexicon();
  };

  const handleDeleteLexiconWord = async (word: string) => {
    await deleteLexiconWord(word);
    await loadLexicon();
  };

  // Word Correction
  const handleCorrectWord = (word: string, context: string) => {
    setCorrectionTarget({ word, context });
    setIsCorrectionOpen(true);
  };

  const handleSaveCorrection = async (original: string, corrected: string) => {
    await recordCorrection(original, corrected, correctionTarget.context);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'correct_word',
          original,
          corrected,
          context: correctionTarget.context,
        })
      );
    }
    setUtterances((prev) =>
      prev.map((u) => {
        const regex = new RegExp(`\\b${original}\\b`, 'gi');
        return {
          ...u,
          text: u.text.replace(regex, corrected),
          words: u.words?.map((w) => (w.w.toLowerCase() === original.toLowerCase() ? { ...w, w: corrected } : w)),
        };
      })
    );
    await loadLexicon();
    setIsCorrectionOpen(false);
  };

  // Speaker Renaming
  const handleRenameSpeaker = (speakerId: string, currentName: string) => {
    setRenameTarget({ id: speakerId, name: currentName });
  };

  const handleSaveSpeakerRename = async (speakerId: string, newName: string) => {
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
    setUtterances((prev) =>
      prev.map((u) =>
        (u.speaker_id === speakerId || u.speaker === speakerId || u.speaker === renameTarget?.name)
          ? { ...u, speaker: newName }
          : u
      )
    );
    setRenameTarget(null);
  };

  // Catch-up Recap
  const handleOpenCatchup = () => {
    setIsCatchupLoading(true);
    setIsCatchupOpen(true);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'catchup' }));
    }
  };

  // Plain Language Simplification
  const handleRequestPlainLanguage = async (uttId: string, text: string) => {
    try {
      const data = await simplifyPlainLanguageApi(text);
      setUtterances((prev) =>
        prev.map((u) => (u.utt_id === uttId ? { ...u, plain_text: data.plain_text } : u))
      );
    } catch (e) {
      console.debug('Failed to simplify language:', e);
    }
  };

  // Decide if showing onboarding Home screen
  const showHomeScreen = !hasStartedSession && utterances.length === 0 && !isListening;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 select-none">
      {/* Top Header */}
      <Header
        isListening={isListening}
        onToggleListening={handleToggleListening}
        deviceRole={deviceRole}
        translateMode={activeMode !== 'captions'}
        onToggleTranslate={() => setIsModeSheetOpen(true)}
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

      {/* Addressed-to-Me Ambient Notification Banner */}
      {activeAlert && (
        <AddressedAlertBanner
          vocative={activeAlert.vocative}
          onDismiss={() => setActiveAlert(null)}
        />
      )}

      {/* Main View Area */}
      {showHomeScreen ? (
        <HomeScreen
          onStart={handleToggleListening}
          activeMode={activeMode}
          onSelectMode={handleSelectMode}
          sourceLang={sourceLang}
          targetLang={targetLang}
          onSelectSourceLang={handleSelectSourceLang}
          onSelectTargetLang={handleSelectTargetLang}
          onSwapLanguages={handleSwapLanguages}
          modelProfile={modelProfile}
          activeProfileName={activeProfileName}
        />
      ) : activeMode === 'conversation' ? (
        <ConversationView
          utterances={utterances}
          streamingState={streamingState}
          sourceLang={sourceLang}
          targetLang={targetLang}
          fontSize={fontSize}
          onSpeakText={handleSpeakText}
        />
      ) : (
        <CaptionStream
          utterances={utterances}
          streamingState={streamingState}
          fontSize={fontSize}
          fontFamily={fontFamily}
          lowConfidenceUnderline={lowConfidenceUnderline}
          plainLanguageMode={plainLanguageMode}
          onCorrectWord={handleCorrectWord}
          onRenameSpeaker={handleRenameSpeaker}
          onRequestPlainLanguage={handleRequestPlainLanguage}
          onSpeakText={handleSpeakText}
        />
      )}

      {/* Quick Replies Drawer */}
      {quickReplies.length > 0 && (
        <QuickRepliesDrawer
          replies={quickReplies}
          onDismiss={() => setQuickReplies([])}
        />
      )}

      {/* Mode Selection Sheet */}
      <ModeSelectorSheet
        isOpen={isModeSheetOpen}
        onClose={() => setIsModeSheetOpen(false)}
        activeMode={activeMode}
        onSelectMode={handleSelectMode}
        sourceLang={sourceLang}
        targetLang={targetLang}
        onSelectSourceLang={handleSelectSourceLang}
        onSelectTargetLang={handleSelectTargetLang}
        onSwapLanguages={handleSwapLanguages}
      />

      {/* Debug Latency HUD (Ctrl+Shift+L) */}
      <DebugHud
        isOpen={isDebugHudOpen}
        onClose={() => setIsDebugHudOpen(false)}
        latencyBreakdown={streamingState?.latency_breakdown}
        modelProfile={modelProfile}
        activeMode={activeMode}
        sourceLang={sourceLang}
        targetLang={targetLang}
        totalSpokenToDisplayMs={totalSpokenToDisplayMs}
      />

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
