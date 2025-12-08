@echo off
REM ============================================
REM Juris Transcritor - FAST Launcher
REM Executa Electron DIRETAMENTE (sem electron-vite overhead)
REM ============================================

REM Muda para o diretório do script
cd /d "%~dp0"

REM Recarrega PATH para incluir Cargo/Rust
set PATH=%PATH%;%USERPROFILE%\.cargo\bin

REM Desabilita verificações desnecessárias
set ELECTRON_NO_UPDATER=1

REM Executa Electron DIRETO no código compilado
REM Isso é 3-5x mais rápido que electron-vite preview!
REM Caminho correto para pnpm + Windows
start "Juris Transcritor" node_modules\.pnpm\electron@31.7.0\node_modules\electron\dist\electron.exe out\main\index.js

REM Sai imediatamente
exit
