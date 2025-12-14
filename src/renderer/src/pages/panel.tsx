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

export function Component() {
  const [visualizerData, setVisualizerData] = useState(() =>
    getInitialVisualizerData(),
  )
  const [recording, setRecording] = useState(false)
  const isConfirmedRef = useRef(false)

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

  const recorderRef = useRef<Recorder | null>(null)

  useEffect(() => {
    if (recorderRef.current) return

    const recorder = (recorderRef.current = new Recorder())

    recorder.on("record-start", () => {
      setRecording(true)
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

    recorder.on("record-end", (blob, duration) => {
      setRecording(false)
      setVisualizerData(() => getInitialVisualizerData())
      tipcClient.recordEvent({ type: "end" })

      if (!isConfirmedRef.current) return

      playSound("end_record")
      transcribeMutation.mutate({
        blob,
        duration,
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
    <div className="flex h-screen dark:text-white">
      {transcribeMutation.isPending ? (
        <div className="flex h-full w-full items-center justify-center">
          <Spinner />
        </div>
      ) : (
        <div
          className={cn(
            "flex h-full w-full items-center justify-center overflow-hidden rounded-full border-4 border-white/10 bg-gradient-to-br from-cyan-500/90 via-blue-600/90 to-purple-600/90 shadow-[0_0_30px_rgba(6,182,212,0.5)] backdrop-blur-xl transition-all duration-300",
            recording && "animate-pulse ring-4 ring-cyan-400/50 shadow-[0_0_50px_rgba(34,211,238,0.8)]",
          )}
        >
          <div className="flex h-12 items-center gap-0.5" dir="rtl">
            {visualizerData
              .slice()
              .reverse()
              .map((rms, index) => {
                return (
                  <div
                    key={index}
                    className={cn(
                      "w-1 shrink-0 rounded-full bg-white/90 shadow-[0_0_10px_rgba(255,255,255,0.8)] transition-all duration-75",
                      rms === -1000 && "bg-white/20 shadow-none h-1",
                    )}
                    style={{
                      height: `${Math.min(100, Math.max(16, rms * 100))}%`,
                    }}
                  />
                )
              })}
          </div>
        </div>
      )}
    </div>
  )
}
