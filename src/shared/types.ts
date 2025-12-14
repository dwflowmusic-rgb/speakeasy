import type { CHAT_PROVIDER_ID, STT_PROVIDER_ID } from "."

export type RecordingHistoryItem = {
  id: string
  createdAt: number
  duration: number
  transcript: string
}

export type Config = {
  shortcut?: "hold-ctrl" | "ctrl-slash"
  autoEnter?: boolean
  hideDockIcon?: boolean

  sttProviderId?: STT_PROVIDER_ID

  openaiApiKey?: string
  openaiBaseUrl?: string

  groqApiKey?: string
  groqBaseUrl?: string

  geminiApiKey?: string
  geminiBaseUrl?: string
  geminiModel?: string // "gemini-flash-lite-latest" | "gemini-1.5-flash-latest" | "gemini-1.5-pro-latest" | "gemini-2.0-flash-exp"

  transcriptPostProcessingEnabled?: boolean
  transcriptPostProcessingProviderId?: CHAT_PROVIDER_ID
  transcriptPostProcessingPrompt?: string
}
