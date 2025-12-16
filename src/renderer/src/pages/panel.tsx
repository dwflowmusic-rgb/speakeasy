import { Spinner } from "@renderer/components/ui/spinner"
import { Recorder } from "@renderer/lib/recorder"
import { playSound } from "@renderer/lib/sound"
import { cn } from "@renderer/lib/utils"
import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { rendererHandlers, tipcClient } from "~/lib/tipc-client"

const VISUALIZER_BUFFER_LENGTH = 16

const getInitialVisualizerData = () =>
  Array<number>(VISUALIZER_BUFFER_LENGTH).fill(-1000)

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

export function Component() {
  const [visualizerData, setVisualizerData] = useState(() =>
    getInitialVisualizerData(),
  )
  const [recording, setRecording] = useState(false)
  const [duration, setDuration] = useState(0) // Duration in seconds
  const isConfirmedRef = useRef(false)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const transcribeMutation = useMutation({
    mutationFn: async ({
      blob,
      duration,
    }: {
      blob: Blob
      duration: number
    }) => {
      await tipcClient.createRecording({
        recording: await blob.arrayBuffer(),
        duration,
        // Persona is now handled via global config based on preset selection in Settings
      })
    },
    onError(error) {
      tipcClient.hidePanelWindow()
      tipcClient.displayError({
        title: error.name,
        message: error.message,
      })
    },
  })

  // Sync ref with state removed (activePersona)

  const recorderRef = useRef<Recorder | null>(null)

  // Timer logic
  useEffect(() => {
    if (recording) {
      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
      setDuration(0)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [recording])

  // Initialize Recorder
  useEffect(() => {
    if (recorderRef.current) return

    const recorder = (recorderRef.current = new Recorder())

    recorder.on("record-start", () => {
      setRecording(true)
      setDuration(0)
      tipcClient.recordEvent({ type: "start" })
    })

    recorder.on("visualizer-data", (rms) => {
      setVisualizerData((prev) => {
        const data = [...prev, rms]
        if (data.length > VISUALIZER_BUFFER_LENGTH) {
          data.shift()
        }
        return data
      })
    })

    recorder.on("record-end", (blob, recDuration) => {
      setRecording(false)
      setVisualizerData(() => getInitialVisualizerData())
      tipcClient.recordEvent({ type: "end" })

      const seconds = recDuration / 1000

      if (!isConfirmedRef.current) {
        return
      }

      // Check 10s rule
      if (seconds < 10) {
        tipcClient.hidePanelWindow()
        console.log("Recording too short (<10s), discarded.")
        new Notification("Gravação Descartada", {
          body: "Mensagem muito curta. Digite para ser mais rápido!"
        })
        return
      }

      playSound("end_record")
      transcribeMutation.mutate({
        blob,
        duration: recDuration,
      })
    })
  }, [])

  useEffect(() => {
    const unlisten = rendererHandlers.startRecording.listen(() => {
      setVisualizerData(() => getInitialVisualizerData())
      recorderRef.current?.startRecording()
    })
    return unlisten
  }, [])

  useEffect(() => {
    const unlisten = rendererHandlers.finishRecording.listen(() => {
      isConfirmedRef.current = true
      recorderRef.current?.stopRecording()
    })
    return unlisten
  }, [])

  useEffect(() => {
    const unlisten = rendererHandlers.stopRecording.listen(() => {
      isConfirmedRef.current = false
      recorderRef.current?.stopRecording()
    })
    return unlisten
  }, [])

  useEffect(() => {
    const unlisten = rendererHandlers.startOrFinishRecording.listen(() => {
      if (recording) {
        isConfirmedRef.current = true
        recorderRef.current?.stopRecording()
      } else {
        tipcClient.showPanelWindow()
        recorderRef.current?.startRecording()
      }
    })
    return unlisten
  }, [recording])

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-transparent">
      {transcribeMutation.isPending ? (
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-black/50 backdrop-blur-md border border-white/10">
          <Spinner className="text-white" />
        </div>
      ) : (
        <div className="relative group">
          {/* Main Orb */}
          <div
            className={cn(
              "flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-black/60 shadow-xl backdrop-blur-xl transition-all duration-300",
              recording && "border-orange-500/50 shadow-[0_0_30px_rgba(249,115,22,0.4)]", // Static Orange border/shadow, NO PULSE
              !recording && "hover:scale-105 hover:bg-black/70"
            )}
          >
            {/* Visualizer / Content inside Orb */}
            <div className="flex flex-col items-center justify-center gap-1">
              {recording ? (
                <>
                  <div className="flex h-6 items-center gap-0.5" dir="rtl">
                    {visualizerData.slice(0, 10).reverse().map((rms, index) => (
                      <div
                        key={index}
                        className={cn("w-1 rounded-full bg-orange-500/80 transition-all duration-75", rms === -1000 && "bg-white/10 h-1")}
                        style={{ height: `${Math.min(24, Math.max(4, rms * 40))}px` }}
                      />
                    ))}
                  </div>
                  <span className={cn("text-xs font-mono font-medium", duration < 10 ? "text-red-400" : "text-orange-500")}>
                    {formatTime(duration)}
                  </span>
                </>
              ) : (
                // Idle State - Static Transparency (No pulse)
                <div className="text-white/80 cursor-default">
                  {/* Static indicator or nothing. User requested: "transparência fixa", "eliminando qualquer tipo de pulsação". 
                            So we render NOTHING or just the Orb background which is already bg-black/60.
                            Maybe a small static dot to show center? Or icon?
                            "A tonalidade preta adotada para o indicador de estado inativo (off) é considerada satisfatória".
                            I'll leave it empty/clean, just the orb background.
                        */}
                </div>
              )}
            </div>
          </div>

          {/* Warning for 10s rule */}
          {recording && duration < 10 && (
            <div className="absolute top-[-25px] left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-bold text-red-500 animate-bounce pointer-events-none">
              Mínimo 10s
            </div>
          )}
        </div>
      )}
    </div>
  )
}
