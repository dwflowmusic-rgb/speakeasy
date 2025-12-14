import {
  getWindowRendererHandlers,
  showPanelWindowAndStartRecording,
  stopRecordingAndHidePanelWindow,
  WINDOWS,
} from "./window"
import { systemPreferences } from "electron"
import { configStore } from "./config"
import { state } from "./state"
import { spawn } from "child_process"
import path from "path"

const rdevPath = path
  .join(
    __dirname,
    `../../resources/bin/whispo-rs${process.env.IS_MAC ? "" : ".exe"}`,
  )
  .replace("app.asar", "app.asar.unpacked")

type RdevEvent = {
  event_type: "KeyPress" | "KeyRelease"
  data: {
    key: "ControlLeft" | "CapsLock" | "BackSlash" | string
  }
  time: {
    secs_since_epoch: number
  }
}

export const writeText = (text: string) => {
  return new Promise<void>((resolve, reject) => {
    const child = spawn(rdevPath, ["write", text])

    child.stdout.on("data", (data) => {
      console.log(`stdout: ${data}`)
    })

    child.stderr.on("data", (data) => {
      console.error(`stderr: ${data}`)
    })

    child.on("close", (code) => {
      // writeText will trigger KeyPress event of the key A
      // I don't know why
      keysPressed.clear()

      if (code === 0) {
        resolve()
      } else {
        reject(new Error(`child process exited with code ${code}`))
      }
    })
  })
}

// Simulate a key press to toggle CapsLock back
const simulateCapsLockToggle = () => {
  return new Promise<void>((resolve) => {
    // Use enigo via whispo-rs to press CapsLock once
    const child = spawn(rdevPath, ["toggle-caps"])
    child.on("close", () => resolve())
    // Fallback timeout in case command doesn't exist
    setTimeout(resolve, 100)
  })
}

export const pressEnter = () => {
  return new Promise<void>((resolve) => {
    const child = spawn(rdevPath, ["press-enter"])
    child.on("close", () => resolve())
  })
}

const parseEvent = (event: any) => {
  try {
    const e = JSON.parse(String(event))
    e.data = JSON.parse(e.data)
    return e as RdevEvent
  } catch {
    return null
  }
}

// keys that are currently pressed down without releasing
const keysPressed = new Map<string, number>()

const hasRecentKeyPress = () => {
  if (keysPressed.size === 0) return false

  const now = Date.now() / 1000
  return [...keysPressed.values()].some((time) => {
    // 10 seconds - for weird cases where KeyRelease is missing
    return now - time < 10
  })
}

export function listenToKeyboardEvents() {
  // ============================================================
  // CAPSLOCK-BASED HOTKEY
  // Hold CapsLock for 800ms -> Start recording
  // Release CapsLock -> Finish recording + revert CapsLock state
  // Quick tap (<800ms) -> Normal CapsLock toggle
  // ============================================================

  let isHoldingCapsLock = false
  let startRecordingTimer: NodeJS.Timeout | undefined
  let capsLockPressTime = 0
  let shouldRevertCapsLock = false

  // Legacy: Ctrl support (for ctrl-slash mode)
  let isPressedCtrlKey = false
  let isHoldingCtrlKey = false

  if (process.env.IS_MAC) {
    if (!systemPreferences.isTrustedAccessibilityClient(false)) {
      return
    }
  }

  const cancelRecordingTimer = () => {
    if (startRecordingTimer) {
      clearTimeout(startRecordingTimer)
      startRecordingTimer = undefined
    }
  }

  const handleEvent = (e: RdevEvent) => {
    const shortcut = configStore.get().shortcut

    if (e.event_type === "KeyPress") {
      // Escape cancels recording
      if (e.data.key === "Escape" && state.isRecording) {
        const win = WINDOWS.get("panel")
        if (win) {
          stopRecordingAndHidePanelWindow()
        }
        return
      }

      // ============================================================
      // CAPSLOCK HOTKEY (default)
      // ============================================================
      if (shortcut !== "ctrl-slash") {
        if (e.data.key === "CapsLock") {
          capsLockPressTime = Date.now()

          if (hasRecentKeyPress()) {
            console.log("[CAPSLOCK] Ignored - other keys pressed")
            return
          }

          if (startRecordingTimer) {
            return
          }

          startRecordingTimer = setTimeout(() => {
            isHoldingCapsLock = true
            shouldRevertCapsLock = true  // We need to revert CapsLock after recording

            console.log("[CAPSLOCK] Start recording")

            showPanelWindowAndStartRecording()
          }, 800)
        } else {
          // Any other key pressed
          keysPressed.set(e.data.key, e.time.secs_since_epoch)
          cancelRecordingTimer()

          // If holding CapsLock and press another key, stop recording
          if (isHoldingCapsLock) {
            stopRecordingAndHidePanelWindow()
          }
          isHoldingCapsLock = false
        }
      }

      // ============================================================
      // CTRL+SLASH HOTKEY (legacy mode)
      // ============================================================
      if (shortcut === "ctrl-slash") {
        if (e.data.key === "ControlLeft") {
          isPressedCtrlKey = true
        }
        if (e.data.key === "Slash" && isPressedCtrlKey) {
          getWindowRendererHandlers("panel")?.startOrFinishRecording.send()
        }
      }

    } else if (e.event_type === "KeyRelease") {
      keysPressed.delete(e.data.key)

      // ============================================================
      // CAPSLOCK RELEASE
      // ============================================================
      if (shortcut !== "ctrl-slash" && e.data.key === "CapsLock") {
        const holdDuration = Date.now() - capsLockPressTime

        cancelRecordingTimer()

        if (isHoldingCapsLock) {
          console.log(`[CAPSLOCK] Release after ${holdDuration}ms - finishing recording`)
          getWindowRendererHandlers("panel")?.finishRecording.send()

          // Revert CapsLock state after a short delay
          // (the recording grab toggled CapsLock, we toggle it back)
          if (shouldRevertCapsLock) {
            setTimeout(() => {
              console.log("[CAPSLOCK] Reverting CapsLock state")
              simulateCapsLockToggle()
            }, 200)
          }
        } else {
          // Quick tap - CapsLock toggled normally by OS, no action needed
          console.log(`[CAPSLOCK] Quick tap (${holdDuration}ms) - normal toggle`)
          stopRecordingAndHidePanelWindow()
        }

        isHoldingCapsLock = false
        shouldRevertCapsLock = false
      }

      // Legacy Ctrl release
      if (shortcut === "ctrl-slash" && e.data.key === "ControlLeft") {
        isPressedCtrlKey = false
      }
    }
  }

  const child = spawn(rdevPath, ["listen"], {})

  child.stdout.on("data", (data) => {
    if (import.meta.env.DEV) {
      console.log(String(data))
    }

    const event = parseEvent(data)
    if (!event) return

    handleEvent(event)
  })

  console.log("[KEYBOARD] Listening for CapsLock hotkey (hold 800ms to record)")
}

