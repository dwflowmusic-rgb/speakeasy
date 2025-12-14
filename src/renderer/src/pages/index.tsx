import { ControlGroup } from "@renderer/components/ui/control"
import { queryClient } from "@renderer/lib/query-client"
import { rendererHandlers, tipcClient } from "@renderer/lib/tipc-client"
import { cn } from "@renderer/lib/utils"
import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useRef, useState } from "react"
import { RecordingHistoryItem } from "@shared/types"
import dayjs from "dayjs"
import { Input } from "@renderer/components/ui/input"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@renderer/components/ui/tooltip"
import { playSound } from "@renderer/lib/sound"

export function Component() {
  const historyQuery = useQuery({
    queryKey: ["recording-history"],
    queryFn: async () => {
      return tipcClient.getRecordingHistory()
    },
  })

  const [keyword, setKeyword] = useState("")

  const today = useMemo(() => dayjs().format("MMM D, YYYY"), [])
  const yesterday = useMemo(
    () => dayjs().subtract(1, "day").format("MMM D, YYYY"),
    [],
  )

  const historyGroupsByDate = useMemo(() => {
    if (!historyQuery.data) return []

    const groups = new Map<string, RecordingHistoryItem[]>()

    for (const item of historyQuery.data) {
      if (
        keyword &&
        !item.transcript.toLowerCase().includes(keyword.toLowerCase())
      ) {
        continue
      }

      const date = dayjs(item.createdAt).format("MMM D, YYYY")

      const items = groups.get(date) || []

      items.push(item)
      groups.set(date, items)
    }

    return [...groups.entries()].map((entry) => {
      return {
        date: entry[0],
        items: entry[1],
      }
    })
  }, [historyQuery.data, keyword])

  useEffect(() => {
    return rendererHandlers.refreshRecordingHistory.listen(() => {
      queryClient.invalidateQueries({
        queryKey: ["recording-history"],
      })
    })
  }, [])

  return (
    <>
      <header className="app-drag-region flex h-14 shrink-0 items-center justify-between border-b border-white/10 bg-black/20 px-6 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.8)]"></div>
          <span className="font-bold tracking-tight text-lg text-white">SpeakEasy</span>
        </div>

        <div className="flex">
          <Input
            wrapperClassName="dark:bg-white/5 border-white/10 focus-within:ring-cyan-500/50"
            className="text-sm"
            placeholder="Search recordings..."
            endContent={
              <span className="i-mingcute-search-2-line text-neutral-400"></span>
            }
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>
      </header>

      {historyGroupsByDate.length === 0 ? (
        <div className="flex grow flex-col items-center justify-center gap-4 text-center font-medium leading-none">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5 shadow-inner">
            <span className="i-mingcute-mic-line text-3xl text-neutral-600"></span>
          </div>
          <span className="mx-auto max-w-md text-xl text-neutral-400">
            No Recordings {keyword ? `For ${JSON.stringify(keyword)}` : ""}
          </span>
          {!keyword && (
            <span className="text-sm text-neutral-600">
              Hold{" "}
              <span className="inline-flex h-6 items-center rounded border border-neutral-700 bg-neutral-800 px-1.5 font-mono text-xs text-neutral-300">
                Ctrl
              </span>{" "}
              to record
            </span>
          )}
        </div>
      ) : (
        <div className="grow overflow-auto px-6 py-6 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/10 hover:scrollbar-thumb-white/20">
          <div className="grid gap-6">
            {historyGroupsByDate.map((group) => {
              return (
                <ControlGroup
                  key={group.date}
                  title={
                    group.date === today
                      ? "Today"
                      : group.date === yesterday
                        ? "Yesterday"
                        : group.date
                  }
                  className="text-cyan-400"
                >
                  <div className="flex flex-col gap-2">
                    {group.items.map((item) => {
                      return (
                        <div
                          key={item.id}
                          className="group flex items-center justify-between gap-4 rounded-xl border border-white/5 bg-white/5 p-4 transition-all hover:bg-white/10 hover:border-white/10 hover:shadow-lg hover:shadow-cyan-900/10"
                        >
                          <TooltipProvider>
                            <Tooltip delayDuration={0} disableHoverableContent>
                              <TooltipTrigger asChild>
                                <span className="inline-flex h-6 shrink-0 cursor-default items-center justify-center rounded-md bg-black/40 px-2 text-xs font-medium text-neutral-400 group-hover:text-cyan-200 transition-colors">
                                  {dayjs(item.createdAt).format("HH:mm")}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="right" className="bg-neutral-900 border-neutral-800 text-neutral-300">
                                Recorded at{" "}
                                {dayjs(item.createdAt).format(
                                  "ddd, MMM D, YYYY h:mm A",
                                )}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <div className="grow select-text text-neutral-300 group-hover:text-white transition-colors line-clamp-2">
                            {item.transcript}
                          </div>
                          <div className="flex shrink-0 gap-1 opacity-60 group-hover:opacity-100 transition-opacity">
                            <PlayButton id={item.id} />

                            <CopyButton transcript={item.transcript} />

                            <DeleteButton id={item.id} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </ControlGroup>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}

const itemButtonVariants = ({ isDanger }: { isDanger?: boolean } = {}) =>
  cn(
    "w-6 h-6 rounded-md inline-flex items-center justify-center text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800 hover:text-black dark:hover:text-white",

    isDanger && "hover:text-red-500 dark:hover:text-red-600",
  )

const PlayButton = ({ id }: { id: string }) => {
  const [status, setStatus] = useState<null | "playing" | "paused">(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const start = () => {
    const audio = (audioRef.current = new Audio())
    audio.src = `assets://recording/${id}`
    audio.addEventListener("play", () => {
      setStatus("playing")
    })
    audio.addEventListener("ended", () => {
      setStatus(null)
    })
    audio.addEventListener("pause", () => {
      setStatus("paused")
    })

    audio.play()
  }

  const pause = () => {
    audioRef.current?.pause()
  }

  return (
    <button
      type="button"
      className={itemButtonVariants()}
      onClick={() => {
        if (status === null) {
          start()
        } else if (status === "playing") {
          pause()
        } else if (status === "paused") {
          audioRef.current?.play()
        }
      }}
    >
      <span
        className={cn(
          status === "playing"
            ? "i-mingcute-pause-fill"
            : "i-mingcute-play-fill",
        )}
      ></span>
    </button>
  )
}

const CopyButton = ({ transcript }: { transcript: string }) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(transcript)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)  // Reset após 2s
    } catch (error) {
      console.error('Falha ao copiar:', error)
    }
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={itemButtonVariants()}
            onClick={handleCopy}
          >
            <span
              className={cn(
                copied ? "i-mingcute-check-fill text-green-500" : "i-mingcute-copy-2-line"
              )}
            ></span>
          </button>
        </TooltipTrigger>
        <TooltipContent>
          {copied ? "Copiado!" : "Copiar texto"}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

const DeleteButton = ({ id }: { id: string }) => {
  return (
    <button
      type="button"
      className={itemButtonVariants({ isDanger: true })}
      onClick={async () => {
        if (window.confirm("Delete this recording forever?")) {
          await tipcClient.deleteRecordingItem({ id })
          queryClient.invalidateQueries({
            queryKey: ["recording-history"],
          })
        }
      }}
    >
      <span className="i-mingcute-delete-2-fill"></span>
    </button>
  )
}
