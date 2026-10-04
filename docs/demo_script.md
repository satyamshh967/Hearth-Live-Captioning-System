# Hearth — 90-Second Demo Video Script & GIF Shot List

---

## 1. 90-Second Demo Video Script

**Title**: *Hearth — Bringing Dadaji Back to the Dinner Table*  
**Duration**: 90 seconds (1:30)  
**Music**: Warm, gentle acoustic guitar background; dips during spoken lines.

| Time | Visual / Screen Action | Voiceover / Audio |
| :---: | :--- | :--- |
| **0:00 - 0:12** | **The Problem**: A bustling family dinner table. Four family members talking, laughing, passing bowls. Close-up on 76-year-old grandfather (Dadaji) quietly looking down at his plate, unable to catch fast-moving dialogue across the table. | *"At family dinners, conversations move fast. For my 76-year-old grandfather, Ramesh—Dadaji—age-related hearing loss meant slowly withdrawing from the banter, missing the jokes, and feeling isolated at his own table."* |
| **0:12 - 0:25** | **The Setup (Table-Mic Mode)**: A phone is set in the center of the table. A tablet is propped up in front of Dadaji. The phone camera scans a quick QR code on the tablet screen. Status badge flashes **"Local Only • Connected"**. | *"This is Hearth: private, offline live captioning built specifically for the family table. A phone acts as the center table-mic, and Dadaji's tablet becomes a clear, high-contrast display."* |
| **0:25 - 0:42** | **Live Speech & Vocabulary Biasing**: Daughter speaks: *"Dadaji, aapne Metformin li kya with warm water?"* Sub-second captions appear on the tablet in large 28px text with speaker tags. Shows Whisper raw vs Hearth: *"Metformin"* and *"Dadaji"* correctly recognized. | *"The real-time path never waits on an LLM. Silero VAD and local faster-whisper stream live captions under one second. Our personal lexicon knows 40+ family names, dishes like Dal makhani, and cardiac medications, rescuing them from ASR errors."* |
| **0:42 - 0:58** | **Addressed-to-Me Alert & Quick Replies**: Someone mentions Dadaji in 3rd person (*"Dadaji went for a walk"*); screen stays calm. Then someone asks: *"Dadaji, thodi aur dal lenge?"* Screen gently glows amber, a soft chime plays, and 3 quick reply chips appear. Dadaji taps *"Haan beta, thodi si"* and the tablet flashes a giant high-contrast response card across the table. | *"Hearth knows the difference between talking ABOUT him and talking TO him. When addressed directly, the screen gently pulses with a chime. And with one tap, Dadaji can reply in his own voice or show a large card without straining."* |
| **0:58 - 1:12** | **"What Did I Miss?" & Doctor Visit Mode**: Dadaji returns from looking away, taps **"What did I miss?"**. A 2-sentence conversational recap pops up. Toggle into **Doctor Visit Mode**: complex terms like *"presbycusis"* and *"postprandial hyperglycemia"* simplify into plain English with original text one tap away. | *"When he drifts away to eat, the 'What did I miss?' button generates a crystal-clear 2-sentence recap. And in Doctor Visit mode, complex jargon is simplified into reassuring everyday language."* |
| **1:12 - 1:30** | **Privacy Proof & Closing**: Close-up of Dadaji smiling, nodding, and passing the roti. Camera cuts to terminal showing zero external network packets and tests passing offline. Screen title: *Hearth — Open Source AI for the Family Table*. | *"Zero cloud servers. Zero telemetry. 100% private, on-device open-source AI. Because everyone deserves a seat—and a voice—at the family table."* |

---

## 2. GIF Shot List (for README & Dev.to Blog Post)

### GIF 1: `table-mic-pairing.gif` (6 seconds)
- **Action**: Tablet displays QR code and room code `TABLE-4821`. Phone scans code; both devices instantly lock into live synchronized caption session.
- **Key Element**: Visible "Local Only" green verified badge.

### GIF 2: `live-caption-stream.gif` (8 seconds)
- **Action**: Speaking Hindi-English code-switched sentence. Rolling partial caption in italic pulses, followed by sub-1s final caption with speaker color bubble (*Priya* in emerald).
- **Key Element**: Low-confidence word with subtle dotted underline; font size slider animating from 18px to 36px.

### GIF 3: `addressed-alert-and-replies.gif` (8 seconds)
- **Action**: Speaker says *"Dadaji, aap thodi aur dal lenge?"*. Screen glows amber, top notification banner slides in, 3 quick reply chips appear at bottom. Tap *"Show Large"* card expanding across screen.
- **Key Element**: Full-screen gold response card.

### GIF 4: `what-did-i-miss.gif` (7 seconds)
- **Action**: Tap purple *"What did I miss?"* button. Modal opens displaying 2-sentence conversational recap with speaker chips (*Priya, Sunita, Rohan*).

### GIF 5: `tap-to-correct-lexicon.gif` (6 seconds)
- **Action**: Tapping misheard word in caption. Popover opens showing original word and input box; typing *"Metformin"*; hitting Save; word updates dynamically in the stream and SQLite lexicon.
