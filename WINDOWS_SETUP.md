# Windows Setup Guide - Whispo

Complete installation guide for Whispo on Windows, including troubleshooting for common issues.

---

## Prerequisites

### Required

- **Windows 10 or 11** (64-bit)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Internet connection** - For API calls

### For Building from Source

- **Rust** - [Install via rustup](https://rustup.rs/)
- **Visual Studio Build Tools** with C++ workload

  ```powershell
  winget install Microsoft.VisualStudio.2022.BuildTools
  ```

---

## Quick Setup (Pre-Compiled Binary)

### 1. Clone Repository

```powershell
git clone https://github.com/giand/whispo-windows.git
cd whispo-windows
```

### 2. Install Dependencies

```powershell
# Install pnpm globally (if not installed)
npm install -g pnpm

# Install project dependencies
pnpm install
```

**Note:** You may see a `node-gyp` error for `@egoist/electron-panel-window`. This is non-blocking and doesn't affect functionality.

### 3. Launch App

```powershell
# Silent mode (no terminal)
.\whispo-silencioso.vbs

# Or with terminal (for debugging)
.\whispo.bat
```

### 4. Configure API Key

1. **Get Free Groq API Key:**
   - Visit: <https://console.groq.com>
   - Create free account
   - API Keys → Create API Key
   - Copy key (starts with `gsk_`)

2. **In Whispo:**
   - Open Settings (tray icon or in-app)
   - Go to **Providers** tab
   - Section **Groq** → Paste API key
   - Go to **General** tab
   - Set **Speech-to-Text Provider** → Groq

### 5. Test Dictation

- Hold `Ctrl` key
- Speak: "Testing dictation"
- Release `Ctrl`
- Text should appear in 1-2 seconds!

---

## Building from Source

### 1. Install Rust

```powershell
# Option 1: winget
winget install Rustlang.Rustup

# Option 2: Direct download
# Visit https://rustup.rs and follow instructions
```

**After install, restart PowerShell or reload PATH:**

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cargo --version  # Should show v1.91.1 or higher
```

### 2. Install C++ Build Tools

```powershell
winget install Microsoft.VisualStudio.2022.BuildTools

# During installation, select:
# - Desktop development with C++
# - Windows 10/11 SDK
```

### 3. Clone and Install Dependencies

```powershell
git clone https://github.com/giand/whispo-windows.git
cd whispo-windows

npm install -g pnpm
pnpm install
```

### 4. Build Rust Audio Engine

```powershell
# Navigate to Rust project
cd whispo-rs

# Build release binary
cargo build --release

# Create destination folder
cd ..
New-Item -ItemType Directory -Force -Path "resources\bin"

# Copy compiled binary
Copy-Item "whispo-rs\target\release\whispo-rs.exe" -Destination "resources\bin\whispo-rs.exe"
```

### 5. Build Electron App

```powershell
# Run Windows fix script
pnpm run fix-pnpm-windows

# Build application
node node_modules\electron-vite\bin\electron-vite.js build
```

### 6. Launch

```powershell
.\whispo-silencioso.vbs
```

---

## Auto-Start Setup

### Option 1: Using Existing Shortcut (Automatic)

A shortcut is automatically created during setup in:

```
C:\Users\YOUR_USERNAME\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
```

### Option 2: Manual Setup

1. **Press `Win + R`**
2. **Type:** `shell:startup`
3. **Right-click** → New → Shortcut
4. **Location:** Path to `whispo-silencioso.vbs`
5. **Name:** Whispo
6. **Click Finish**

### Verify Auto-Start

Restart Windows. Whispo should launch automatically in the system tray.

---

## Troubleshooting

### 1. Cargo Not Found After Rust Install

**Problem:** `cargo: command not found`

**Solution:**

```powershell
# Reload PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verify
cargo --version
```

**Alternative:** Restart PowerShell completely.

---

### 2. electron-builder Fails with 7-Zip Error

**Problem:**

```
ERROR: Cannot create directory
7-Zip ... workingDir=C:\Users\...\Área de...
```

**Root Cause:** Special characters in path ("Área")

**Solutions:**

**Option A: Move Project to Simple Path**

```powershell
# Move to C:\
Move-Item "C:\Users\...\Área de Trabalho\...\whispo" "C:\whispo"
cd C:\whispo
```

**Option B: Use Manual Build (Current Method)**

- Use `whispo.bat` and `whispo-silencioso.vbs`
- Skip electron-builder entirely
- Works perfectly for local use!

---

### 3. Node-gyp Error for electron-panel-window

**Error:**

```
ELIFECYCLE Command failed with exit code 1.
gyp ERR! node-gyp -v v10.2.0
```

**Impact:** Non-blocking. Application works fine.

**Fix (Optional):**

```powershell
# Install Windows Build Tools
npm install --global --production windows-build-tools

# Retry
pnpm install
```

---

### 4. Electron Binary Not Found

**Problem:** `Error: Electron uninstall`

**Solution:**

```powershell
# Manual postinstall
cd node_modules\.pnpm\electron@31.7.0\node_modules\electron
node install.js
cd ..\..\..\..
```

---

### 5. Terminal Window Stays Open

**Problem:** `whispo.bat` shows console window

**Solution:** Use `whispo-silencioso.vbs` instead

```powershell
# Update Desktop shortcut to point to .vbs file

**Long-term Solution:**

```powershell
# Move project to path without accents
Move-Item "current-path" "C:\whispo"
# or
Move-Item "current-path" "C:\Projects\whispo"
```

**Immediate Workaround:**

- Use current manual setup (works fine!)
- Avoid running electron-builder

---

## Configuration Tips

### Change Shortcut

**Default:** Hold Ctrl

**Alternative:** Ctrl + /

1. Settings → General
2. Shortcut → Select "Ctrl + /"
3. Now press `Ctrl+/` to start, speak, `Ctrl+/` to stop

### Post-Processing with LLM

**Automatically improve transcription:**

1. Settings → General
2. Enable "Transcript Post-Processing"
3. Select Provider (OpenAI/Groq/Gemini)
4. Edit Prompt:

   ```
   Fix grammar and punctuation: {transcript}
   ```

**Advanced Prompt Example:**

```
You are a professional transcription editor. 
Improve this transcript:
- Fix grammar and spelling
- Add proper punctuation  
- Format as paragraphs if needed
- Keep the original meaning

Transcript: {transcript}
```

### Multiple Providers

You can configure all three providers and switch between them:

- **Groq** - Free, fast (recommended)
- **OpenAI** - Most accurate, paid
- **Gemini** - Google ecosystem, free tier

Configure all in Providers, switch in General settings.

---

## Performance Optimization

### Faster Startup

1. **Keep App Running:**
   - Don't close, minimize to tray
   - Uses ~200MB RAM idle

2. **SSD Recommended:**
   - Faster Electron startup
   - Quicker Rust binary load

### Better Transcription

1. **Good Microphone:**
   - USB microphone recommended
   - Built-in laptop mic works but less accurate

2. **Quiet Environment:**
   - Background noise affects accuracy
   - Whisper is good but not perfect

3. **Clear Speech:**
   - Speak at normal pace
   - Enunciate clearly
   - Avoid filler words

---

## Uninstall

### Remove Auto-Start

```powershell
# Press Win + R, type:
shell:startup

# Delete "Whispo.lnk" shortcut
```

### Remove Desktop Shortcut

Delete "Whispo" shortcut from Desktop

### Remove Application

```powershell
# Delete project folder
Remove-Item -Recurse -Force "C:\path\to\whispo-windows"
```

### Remove Global Tools

```powershell
# Remove pnpm (optional)
npm uninstall -g pnpm

# Remove Rust (optional)
rustup self uninstall
```

---

## FAQ

**Q: Does it work offline?**
A: No, requires internet for API calls to transcription service.

**Q: Is my voice data stored?**
A: Only locally in app. API providers (Groq/OpenAI) process audio but claim not to store it. Check their privacy policies.

**Q: Can I use without API key?**
A: No, transcription requires external API (OpenAI Whisper).

**Q: Is Groq really free?**
A: Yes, free tier is generous (6000 tokens/min). No credit card required.

**Q: Can I change language?**
A: Whisper auto-detects language. Supports 50+ languages including Portuguese, Spanish, French, etc.

**Q: Works with all apps?**
A: Yes, any app that accepts text input (Word, email, chat, IDE, etc.)

**Q: Can I use multiple shortcuts?**
A: No, only one active shortcut at a time. Choose Hold Ctrl OR Ctrl+/.

---

## Support

**Issues:** <https://github.com/giand/whispo-windows/issues>
**Original Project:** <https://github.com/egoist/whispo>
**Groq Support:** <https://console.groq.com>

---

**Last Updated:** December 2025 | **Version:** 1.0.0
