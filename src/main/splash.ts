import { BrowserWindow } from "electron"
import path from "path"

let splashWindow: BrowserWindow | null = null

export function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 400,
        height: 300,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    })

    const splashPath = path
        .join(__dirname, "../../resources/splash.html")
        .replace("app.asar", "app.asar.unpacked")
    splashWindow.loadFile(splashPath)

    return splashWindow
}

export function closeSplashWindow() {
    if (splashWindow && !splashWindow.isDestroyed()) {
        splashWindow.close()
        splashWindow = null
    }
}
