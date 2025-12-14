# Changelog

All notable changes to Juris Transcritor (formerly Whispo Windows) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.2.0] - 2025-12-08

### Added

- **CapsLock Hotkey**: New recording activation method
  - **Hold CapsLock for 800ms** → Start recording
  - **Release CapsLock** → Stop and transcribe
  - **Quick tap** → Normal CapsLock toggle (caps on/off)
  - Replaces Ctrl-hold which conflicted with file selection
- **Clipboard-based Text Injection**: Ultra-fast text paste
  - Uses Ctrl+V instead of character-by-character simulation
  - **Performance:** 2-5 seconds → < 100ms (95%+ faster!)
  - Preserves and restores original clipboard content
  - No more focus-loss issues during text insertion
- **Toggle-caps Command**: New Rust command for CapsLock control

### Changed

- **LLM Post-Processing**: Completely rewritten for reliability
  - Proper system/user message separation (was causing command echo)
  - Added `SYSTEM_INSTRUCTION` constant with clear rules
  - Response cleanup removes unwanted prefixes ("Aqui está:", etc.)
  - Graceful fallback to original transcript on error
  - Better logging for debugging

### Fixed

- **"LLM returns command text"** - Fixed! Now properly separates instructions from content
- **"Text injection stops on focus loss"** - Fixed! Clipboard paste is atomic
- **"Slow character-by-character typing"** - Fixed! Now uses Ctrl+V
- **"Ctrl conflicts with file selection"** - Fixed! Now uses CapsLock

### Technical

- Modified `src/main/keyboard.ts` - CapsLock detection with 800ms threshold
- Rewrote `src/main/llm.ts` - Proper OpenAI/Gemini message structure
- Updated `whispo-rs/src/main.rs`:
  - New `write_text_fast()` using clipboard + Ctrl+V
  - New `toggle-caps` command for CapsLock simulation
  - Added `clipboard-win` dependency
- Rebuilt Rust binary with clipboard support

### Performance

| Feature | Before | After | Improvement |
|---------|--------|-------|-------------|
| Text Injection | 2-5s | < 100ms | **95-98%** |
| Focus Loss | Common | None | **100%** |
| Ctrl Conflicts | Frequent | None | **100%** |

---

## [1.1.1] - 2025-12-08

### Added

- **Copy Button in History**: New copy button (📋) in transcript history with visual feedback
  - Click to copy transcript to clipboard
  - Green checkmark (✓) confirmation
  - Tooltip: "Copiar texto" / "Copiado!"
  - Fallback when auto-insert fails due to permissions
- **Fast Launcher**: Direct Electron execution bypassing electron-vite overhead
  - `juris-transcritor-fast.bat` - Executes Electron directly on compiled code
  - `juris-transcritor-fast-silencioso.vbs` - Silent version
  - **Performance**: 80-90% faster startup (18s → 3-5s)
- **Single Instance Lock**: Prevents duplicate processes
  - Second launch focuses existing window instead of creating new instance
  - Clean user experience on double-click
- **Startup Profiling**: Console markers to measure initialization time
  - Detailed timing for each module load
  - Visible via DevTools Console (Ctrl+Shift+I)

### Changed

- **Rebranding**: Whispo → Juris Transcritor
  - Application name updated throughout codebase
  - Window title: "Juris Transcritor"
  - System tray tooltip: "Juris Transcritor"
  - Package name: `juris-transcritor`
  - AppID: `com.juristranscritor.app`
  - Version bump: 0.1.7 → 1.1.0 → 1.1.1
- **Background Startup**: Application starts minimized to system tray only
  - No window popup on launch
  - Click tray icon to open interface
  - Less intrusive user experience
- **Lazy Loading**: Heavy modules load asynchronously after UI
  - Keyboard events listener (Rust binary)
  - System tray menu
  - Update checker
  - Faster perceived startup
- **Gemini Model Upgrade**: `gemini-1.5-flash-002` → `gemini-flash-lite-latest`
  - Points to `gemini-2.5-flash-lite-preview-09-2025`
  - Faster grammar/spelling corrections
  - Lower cost ($0.10/$0.40 per 1M tokens)
  - Latest model (Jan 2025 knowledge cutoff)

### Removed

- **Obsolete Launchers**: Removed slow electron-vite-based scripts
  - `whispo.bat` (18s startup)
  - `whispo-silencioso.vbs` (wrapper for slow launcher)
  - Superseded by fast launchers

### Performance

- **Startup Time**: 30s → 3-5s (83-90% improvement)
- **Memory**: Eliminated 135MB Node.js overhead from electron-vite
- **User Experience**: Instant responsiveness, no lag

### Technical

- Updated `src/main/index.ts` with single instance lock and lazy loading
- Modified `src/main/window.ts` for background startup support
- Enhanced `src/renderer/src/pages/index.tsx` with CopyButton component
- Optimized `src/main/llm.ts` with latest Gemini model

### Known Issues & Next Version Roadmap

**For v1.2.0+ (Future):**

- 🔧 **PRIORITY**: Change default hotkey from Ctrl (conflicts with file selection)
  - Explore alternatives: Ctrl+Shift+Space, Windows key combinations, F-keys
  - User reports activation when selecting multiple files
- Add "About" page with proper Whispo attribution
- Design custom legal-themed icon
- Consider moving to simple path for native .exe distribution (electron-builder)

## [1.0.0] - 2025-12-04

### Added

- **Windows Silent Launcher**: `whispo-silencioso.vbs` script that launches Whispo without showing terminal window
- **Windows Batch Launcher**: `whispo.bat` script with automatic Rust/Cargo PATH configuration
- **Auto-start Configuration**: Shortcut in Windows Startup folder for automatic launch on system boot
- **Compiled Rust Binary**: Pre-compiled `whispo-rs.exe` included in `resources/bin/` for Windows x64
- **Comprehensive Documentation**: Portuguese and English README with Windows-specific setup instructions
- **Windows Setup Guide**: Detailed `WINDOWS_SETUP.md` with step-by-step installation process
- **Enhanced .gitignore**: Windows-specific patterns (Thumbs.db, desktop.ini) and IDE exclusions

### Changed

- Modified original `build-rs` shell script workflow to manual Rust compilation for Windows compatibility
- Configured Groq API as default transcription provider (free tier)
- Updated launcher shortcuts to use silent VBS script instead of BAT (better UX)

### Fixed

- **Path Issues**: Resolved Rust/Cargo PATH not available in Windows sessions
- **Terminal Window**: Eliminated persistent console window during application runtime
- **Electron Installation**: Manually executed postinstall script to fix binary download failure
- **Application Structure**: Fixed module path issues in packaged application (out/main/index.js)
- **7-Zip Path Bug**: Workaround for electron-builder failure with special characters in path ("Área")

### Technical

- **Stack**: Electron 31.0.2, TypeScript, React, Tailwind CSS, Rust (whispo-rs)
- **Dependencies**: Successfully installed via pnpm despite node-gyp error in electron-panel-window
- **Build Process**: electron-vite build completed in ~2.7s for production bundle
- **Rust Compilation**: Manual cargo build --release completed in 30.56s

### Known Issues

- `@egoist/electron-panel-window` module fails to compile with node-gyp (non-blocking)
- electron-builder fails when project path contains special characters (Área)
- Requires manual Rust compilation on first setup (not automated)

### Configuration

- Supports multiple transcription providers: OpenAI, Groq (default), Gemini
- Transcription via OpenAI Whisper API
- Optional post-processing with LLMs (GPT-4o-mini, Llama-3.1-70b, Gemini)
- Customizable shortcut: Hold Ctrl (default) or Ctrl+/ toggle

---

## Upstream Reference

This is a Windows-customized fork of [egoist/whispo](https://github.com/egoist/whispo) v0.1.7.

Original project: AI-powered dictation tool for macOS and Windows.

Windows-specific enhancements focus on silent execution, auto-start, and seamless Windows integration.
