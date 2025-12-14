import { Control, ControlGroup } from "@renderer/components/ui/control"
import { Input } from "@renderer/components/ui/input"
import { HelpButton } from "../components/HelpButton"
import {
  useConfigQuery,
  useSaveConfigMutation,
} from "@renderer/lib/query-client"
import { Config } from "@shared/types"

export function Component() {
  const configQuery = useConfigQuery()
  const saveConfigMutation = useSaveConfigMutation()

  const saveConfig = (config: Partial<Config>) => {
    saveConfigMutation.mutate({
      config: {
        ...configQuery.data,
        ...config,
      },
    })
  }

  if (!configQuery.data) return null

  return (
    <div className="grid gap-4">
      <ControlGroup className="mb-4" title={
        <div className="flex items-center gap-2">
          OpenAI
          <HelpButton module="openai" />
        </div>
      }>
        <Control label="API Key" className="px-3">
          <Input
            type="password"
            defaultValue={configQuery.data.openaiApiKey}
            onChange={(e) => {
              saveConfig({
                openaiApiKey: e.currentTarget.value,
              })
            }}
            placeholder="sk-..."
          />
        </Control>
        <Control label="API Base URL" className="px-3">
          <Input
            type="url"
            placeholder="https://api.openai.com/v1"
            defaultValue={configQuery.data.openaiBaseUrl}
            onChange={(e) => {
              saveConfig({
                openaiBaseUrl: e.currentTarget.value,
              })
            }}
          />
        </Control>
      </ControlGroup>

      <ControlGroup className="mb-4" title={
        <div className="flex items-center gap-2">
          Groq
          <HelpButton module="groq" />
        </div>
      }>
        <Control label="API Key" className="px-3">
          <Input
            type="password"
            defaultValue={configQuery.data.groqApiKey}
            onChange={(e) => {
              saveConfig({
                groqApiKey: e.currentTarget.value,
              })
            }}
            placeholder="gsk_..."
          />
        </Control>
        <Control label="API Base URL" className="px-3">
          <Input
            type="url"
            placeholder="https://api.groq.com/openai/v1"
            defaultValue={configQuery.data.groqBaseUrl}
            onChange={(e) => {
              saveConfig({
                groqBaseUrl: e.currentTarget.value,
              })
            }}
          />
        </Control>
      </ControlGroup>

      <ControlGroup title={
        <div className="flex items-center gap-2">
          Gemini (Google)
          <HelpButton module="gemini" />
        </div>
      }>
        <div className="space-y-4 px-3">
          <Control label="API Key" className="p-0 border-none">
            <Input
              type="password"
              defaultValue={configQuery.data.geminiApiKey}
              onChange={(e) => {
                saveConfig({
                  geminiApiKey: e.currentTarget.value,
                })
              }}
              placeholder="AIza..."
            />
          </Control>

          <Control label="API Base URL" className="p-0 border-none">
            <Input
              type="url"
              placeholder="https://generativelanguage.googleapis.com"
              defaultValue={configQuery.data.geminiBaseUrl}
              onChange={(e) => {
                saveConfig({
                  geminiBaseUrl: e.currentTarget.value,
                })
              }}
            />
          </Control>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">Modelo</label>
            <select
              className="flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1"
              title="Selecione o modelo Gemini"
              defaultValue={configQuery.data.geminiModel || "models/gemini-flash-lite-latest"}
              onChange={(e) => {
                saveConfig({
                  geminiModel: e.currentTarget.value,
                })
              }}
            >
              <option value="models/gemini-flash-lite-latest">Flash Lite (Rápido/Barato)</option>
              <option value="models/gemini-flash-latest">Flash (Equilibrado/Padrão)</option>
              <option value="models/gemini-2.5-pro">Pro 2.5 (Avançado)</option>
              <option value="models/gemini-3-pro-preview">Pro 3.0 Preview (Mais Avançado)</option>
            </select>
          </div>
        </div>
      </ControlGroup>
    </div>
  )
}
