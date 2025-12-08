import { app, Menu } from "electron"
import { electronApp, optimizer } from "@electron-toolkit/utils"
import {
  createMainWindow,
  createPanelWindow,
  createSetupWindow,
  makePanelWindowClosable,
  WINDOWS,
} from "./window"
import { listenToKeyboardEvents } from "./keyboard"
import { registerIpcMain } from "@egoist/tipc/main"
import { router } from "./tipc"
import { registerServeProtocol, registerServeSchema } from "./serve"
import { createAppMenu } from "./menu"
import { initTray } from "./tray"
import { isAccessibilityGranted } from "./utils"

registerServeSchema()

// ============================================================
// SINGLE INSTANCE LOCK - Previne múltiplas instâncias
// ============================================================
const gotTheLock = app.requestSingleInstanceLock()

if (!gotTheLock) {
  // Já existe outra instância rodando - sai imediatamente
  console.log("[STARTUP] Another instance is already running, quitting...")
  app.quit()
} else {
  // Primeira instância - Handle caso usuário tente abrir de novo
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    console.log("[SECOND-INSTANCE] User tried to open app again, focusing existing window")

    // Foca na janela principal se ela existir
    const mainWindow = WINDOWS.get("main")
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore()
      }
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
console.time("[STARTUP] Total app initialization")
app.whenReady().then(() => {
  // Set app user model id for windows
  electronApp.setAppUserModelId(process.env.APP_ID)

  const accessibilityGranted = isAccessibilityGranted()

  Menu.setApplicationMenu(createAppMenu())

  registerIpcMain(router)

  registerServeProtocol()

  console.time("[STARTUP] Creating main window")
  if (accessibilityGranted) {
    createMainWindow({ showOnStartup: false })  // Inicia apenas na bandeja
  } else {
    createSetupWindow()
  }
  console.timeEnd("[STARTUP] Creating main window")

  console.time("[STARTUP] Creating panel window")
  createPanelWindow()
  console.timeEnd("[STARTUP] Creating panel window")

  // ============================================================
  // LAZY LOADING - Carrega módulos pesados DEPOIS do startup
  // Executa após o event loop liberar (não bloqueia UI)
  // ============================================================
  setImmediate(() => {
    console.time("[STARTUP] Loading keyboard events")
    listenToKeyboardEvents()
    console.timeEnd("[STARTUP] Loading keyboard events")
  })

  setImmediate(() => {
    console.time("[STARTUP] Loading tray")
    initTray()
    console.timeEnd("[STARTUP] Loading tray")
  })

  setImmediate(() => {
    console.time("[STARTUP] Loading updater")
    import("./updater").then((res) => {
      res.init()
      console.timeEnd("[STARTUP] Loading updater")
    }).catch((err) => {
      console.error("[STARTUP] Updater failed:", err)
    })
  })

  // Marca final do startup - tudo carregado
  console.timeEnd("[STARTUP] Total app initialization")

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on("browser-window-created", (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  app.on("activate", function () {
    if (accessibilityGranted) {
      if (!WINDOWS.get("main")) {
        createMainWindow()
      }
    } else {
      if (!WINDOWS.get("setup")) {
        createSetupWindow()
      }
    }
  })

  app.on("before-quit", () => {
    makePanelWindowClosable()
  })
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit()
  }
})

// In this file you can include the rest of your app"s specific main process
// code. You can also put them in separate files and require them here.
