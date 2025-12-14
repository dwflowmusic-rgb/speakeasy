# 🗺️ Roadmap - Juris Transcritor

Este documento descreve o plano estratégico de evolução do projeto, incluindo novas funcionalidades, melhorias técnicas e dívidas técnicas conhecidas.

## 🔴 Crítico / Bloqueante

*Items que impedem o uso pleno ou oferecem risco.*

- [ ] **Resolving Build Infra (winCodeSign):** O processo de build automático no Windows (`electron-builder`) falha frequentemente ao baixar ferramentas de assinatura (`winCodeSign`) em redes restritas.
  - *Ação:* Investigar configuração de mirror ou incluir tools no repositório (vendoring) se a licença permitir.
- [ ] **Code Signing Certificate:** O executável gerado não é assinado digitalmente, o que dispara o alerta "SmartScreen" do Windows Defender.
  - *Ação:* Adquirir certificado EV ou Standard Code Signing para distribuição profissional.

## 🟡 Importante / Alto Impacto

*Features que agregam valor significativo.*

- [ ] **Modo Offline (Ollama/LocalLLM):** Permitir o uso de modelos locais (Llama 3, Mistral) rodando na máquina do usuário para privacidade total sem depender de APIs externas.
  - *Complexidade:* Alta (requer integrar servidor de inferência local ou conectar a Olama.ai).
- [ ] **Suporte Cross-Platform:** O código Rust (`whispo-rs`) já usa crates compatíveis (`rdev`), mas o build script e os atalhos precisam de testes no Linux e macOS.
  - *Status:* Parcialmente implementado, mas não validado.

## 🟢 Desejável / Futuro

*Melhorias de qualidade de vida e otimizações.*

- [ ] **Editor de Prompt Visual:** Interface gráfica para editar o System Prompt sem precisar escrever texto cru.
- [ ] **Histórico de Transcrições com Pesquisa:** Banco de dados local (SQLite) para salvar e buscar ditados antigos.
- [ ] **Personalização de Atalhos:** Permitir que o usuário escolha outra tecla além do `CapsLock` (ex: Botão lateral do mouse).

## 📝 Dívida Técnica

- **Testes Automatizados:** O projeto carece de testes unitários para o frontend (React) e integração para o Rust.
- **Tipagem Estrita:** Alguns pontos do código usam `any` implícito ou asserções de tipo que poderiam ser mais seguras.

---
*Última atualização: Versão 1.3.0*
