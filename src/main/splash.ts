import { BrowserWindow, app } from "electron"
import path from "path"

let splashWindow: BrowserWindow | null = null

export function createSplashWindow(): BrowserWindow {
    splashWindow = new BrowserWindow({
        width: 300,
        height: 300,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    })

    // Carregar o HTML da splash
    const splashPath = app.isPackaged
        ? path.join(process.resourcesPath, "app.asar.unpacked", "resources", "splash.html")
        : path.join(__dirname, "../../resources/splash.html")

    splashWindow.loadFile(splashPath)
    splashWindow.center()

    return splashWindow
}

export function closeSplashWindow() {
    if (splashWindow) {
        splashWindow.close()
        splashWindow = null
    }
}
