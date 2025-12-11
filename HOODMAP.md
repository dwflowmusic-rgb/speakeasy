# 🗺️ HoodMap - Mapa do Capô

Bem-vindo aos bastidores do **Juris Transcritor**. Este documento mapeia a estrutura de pastas e arquivos para ajudar desenvolvedores a navegar no código.

## 📂 Estrutura Principal

```graphql
whispo/
├── .github/                 # Workflows de CI/CD (GitHub Actions)
├── builds/                  # Saída dos arquivos compilados (dist)
├── resources/               # Arquivos estáticos e binários externos
│   ├── bin/                 # Binários Rust compilados (whispo-rs.exe)
│   ├── splash.html          # Tela de carregamento (HTML/CSS/JS puro)
│   └── icon.png             # Ícones do aplicativo
├── src/
│   ├── main/                # 🧠 PROCESSO PRINCIPAL (Node.js/Electron)
│   │   ├── index.ts         # Ponto de entrada (Startup, Janelas, Tray)
│   │   ├── keyboard.ts      # Gerenciamento de atalhos e hook global
│   │   ├── llm.ts           # Inteligência Artificial (Gemini, OpenAI)
│   │   ├── splash.ts        # Controle da janela de Splash
│   │   ├── config.ts        # Persistência de dados (config.json)
│   │   └── window.ts        # Criação e gestão de janelas (BrowserWindows)
│   ├── preload/             # 🌉 PONTE (Preload Scripts)
│   │   └── index.ts         # Exposição segura de APIs para o Renderer
│   ├── renderer/            # 🎨 INTERFACE (React + Tailwind)
│   │   ├── src/
│   │   │   ├── components/  # Componentes reutilizáveis (UI)
│   │   │   ├── pages/       # Páginas da aplicação (Settings, Home)
│   │   │   └── main.tsx     # Entry point do React
│   └── shared/              # 🤝 Tipos e constantes compartilhados
│       └── types.ts         # Definições typescript (Config, Events)
├── whispo-rs/               # 🦀 MOTOR RUST
│   ├── src/
│   │   └── main.rs          # Código nativo (Hook de teclado e Injeção de texto)
│   └── Cargo.toml           # Dependências Rust
├── electron-builder.config  # Configuração de empacotamento (.exe/.dmg)
└── package.json             # Dependências Node.js e scripts
```

## 🔑 Arquivos Chave

* **`src/main/keyboard.ts`**: O maestro. Coordena quando ouvir e quando parar, chamando o binário Rust.
* **`whispo-rs/src/main.rs`**: O operário. Escuta o teclado em baixo nível e simula a digitação (Ctrl+V).
* **`src/main/llm.ts`**: O cérebro. Recebe texto bruto e transforma em texto jurídico polido usando IA.
* **`resources/bin`**: Onde vive o executável auxiliar que o Electron invoca para tarefas de sistema.

---
*Este mapa reflete a versão 1.3.0 do Juris Transcritor.*
