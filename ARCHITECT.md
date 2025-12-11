# 🏛️ Architect - Arquitetura do Sistema

Este documento descreve as decisões técnicas, o fluxo de dados e os princípios de design do **Juris Transcritor v1.3.0**.

## 🎯 Objetivo

Criar uma ferramenta de ditado de alta performance, focada em privacidade (BYOK - Bring Your Own Key) e invisibilidade (funciona em qualquer campo de texto), superando as limitações dos ditadores nativos do Windows.

## 🏗️ Stack Tecnológica (Híbrida)

O sistema utiliza uma arquitetura híbrida para obter o melhor de dois mundos:

1. **Electron (Node.js):** Gerencia a interface, configurações, chamadas de API (HTTP) e orquestração.
2. **Rust (Nativo):** Lida com tarefas de baixo nível críticas para performance e integração com o SO (Hooks de teclado globais e injeção de texto).

| Camada | Tecnologia | Responsabilidade |
| :--- | :--- | :--- |
| **UI** | React + Tailwind | Configurações amigáveis e feedback visual. |
| **Core** | Electron (Main) | Lógica de negócios, IPC, Gestão de Janelas. |
| **AI** | Google Gemini / OpenAI | Processamento de Linguagem Natural (LLM). |
| **System** | Rust (`rdev`, `enigo`) | Escuta global de teclas (interceptação) e simulação de input. |

## 🔄 Fluxo de Dados (O Ciclo do Ditado)

1. **Interceptação (Rust):**
    * O binário Rust roda em modo "listen", monitorando o estado da tecla `CapsLock`.
    * Ao detectar `CapsLock` pressionado (HOLD), ele avisa o Electron.

2. **Captura de Áudio (Electron/WebAPI):**
    * O Electron ativa o microfone usando a Web Audio API (no Renderer invisível).
    * O áudio é convertido em texto em tempo real (STT) usando *Whisper* (via API Groq/OpenAI).

3. **Processamento (LLM):**
    * O texto transcrito "bruto" (sem pontuação, com gírias) é enviado para o módulo `src/main/llm.ts`.
    * O módulo consulta a configuração (API Key, Modelo, Prompt).
    * Envia para a LLM (ex: Gemini Flash Lite) com um System Prompt especializado (ex: "Formate como texto jurídico").

4. **Injeção (Electron -> Rust):**
    * O texto formatado retorna ao Electron.
    * O Electron chama o binário Rust em modo "write" (`whispo-rs write "texto"`).
    * **Injeção Inteligente:** O Rust coloca o texto na Área de Transferência e simula `Ctrl+V` instantâneo. Isso é 100x mais rápido que simular tecla por tecla e suporta caracteres especiais (acentos, emojis) perfeitamente.

## 🧠 Decisões Arquiteturais Chave

### 1. Por que Rust separado?

Node.js não tem suporte nativo robusto e performático para Hooks Globais de teclado sem travar a UI Event Loop. O binário Rust roda em processo separado (`spawn`), garantindo que a interface do Electron nunca engasgue, mesmo digitando textos longos.

### 2. Injeção via Clipboard vs Datilografia

Simular digitação letra por letra (`k`, `e`, `y`) é lento e propenso a falhas com layouts de teclado diferentes (ABNT2 vs US).
**Decisão:** Usar `Clipboard + Paste`. É atômico, rápido e imune a layout de teclado.

### 3. Splash Screen Nativa

Para dar feedback instantâneo ( < 500ms), usamos uma janela leve com HTML estático carregada *antes* de iniciar os frameworks pesados (React/Vite). Isso melhora a percepção de performance.

### 4. Privacy-First

Nenhum áudio ou texto é salvo em nossos servidores. Tudo trafega direto da máquina do usuário para a API do provedor escolhido (Google/OpenAI). As chaves ficam salvas apenas localmente (`config.json`).

---
*Documento gerado para a comunidade Open Source. Sinta-se livre para contribuir!*
