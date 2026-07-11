const { app, BrowserWindow, Menu, shell, dialog } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');

// ── The single source of truth for where DericBI lives ────────────────────
// This is your live Render deployment. The desktop app is a native window
// pointed at it — no local Python, no bundled server, nothing to keep in
// sync. Content updates (new pages, features, fixes) show up automatically
// on next reload whenever Render redeploys — no installer update needed
// for that.
//
// The auto-updater below is a SEPARATE, second thing: it checks GitHub
// Releases for a newer version of the desktop SHELL itself (window
// behaviour, menu, icon) and offers to download + install it, the same way
// Chrome or Slack update themselves. Most releases will only ever touch
// the web app, so this will rarely have anything new to offer — that's
// expected and fine.
const DERICBI_URL = 'https://dericbi-analytics.onrender.com';

let mainWindow;
let isManualUpdateCheck = false;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1000,
    minHeight: 650,
    show: false,
    backgroundColor: '#f8fafb',
    icon: path.join(__dirname, 'build', 'icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: false,
    },
  });

  mainWindow.once('ready-to-show', () => mainWindow.show());

  mainWindow.loadURL(DERICBI_URL);

  // Any link that tries to open a NEW window (target=_blank, external links)
  // opens in the user's normal browser instead of a second Electron window.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // If Render is asleep (free tier cold start) or offline, show a clear
  // message instead of a blank/broken window.
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    if (errorCode === -3) return; // aborted load (e.g. redirect), ignore
    mainWindow.loadURL(`data:text/html,${encodeURIComponent(`
      <html><body style="font-family:Segoe UI,sans-serif;background:#f8fafb;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
        <div style="text-align:center;color:#374151;">
          <h2 style="color:#3e8865;">DericBI is unreachable</h2>
          <p>${errorDescription || 'Could not connect'}</p>
          <p style="font-size:13px;color:#9ca3af;">
            Check your internet connection, then click Reload below.<br/>
            If DericBI was recently idle, the server may take up to a minute to wake up.
          </p>
          <button onclick="location.reload()" style="margin-top:16px;padding:10px 24px;
            background:#3e8865;color:#fff;border:none;border-radius:6px;
            font-size:14px;cursor:pointer;">Reload</button>
        </div>
      </body></html>
    `)}`);
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Menu bar ──────────────────────────────────────────────────────────────
function buildMenu() {
  const template = [
    {
      label: 'DericBI',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow && mainWindow.loadURL(DERICBI_URL),
        },
        {
          label: 'Check for Updates...',
          click: () => checkForUpdatesManually(),
        },
        {
          label: 'Open in Browser',
          click: () => shell.openExternal(DERICBI_URL),
        },
        { type: 'separator' },
        {
          label: 'About DericBI',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              title: 'About DericBI',
              message: 'DericBI Analytics Engine',
              detail: `Desktop app v${app.getVersion()}\nCut Through Noise\n\n` +
                      `This app connects to your live DericBI deployment at:\n${DERICBI_URL}`,
            });
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' }, { role: 'redo' }, { type: 'separator' },
        { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'zoomIn' }, { role: 'zoomOut' }, { role: 'resetZoom' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
        { role: 'toggleDevTools' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── Auto-update: check → ask → download → ask → install on quit ───────────
// Never auto-downloads or force-installs without asking. If the user says
// "Later" at the download-complete step, it still installs silently the
// next time they quit the app (autoInstallOnAppQuit), so they're never
// stuck on an old version indefinitely, but they're also never interrupted
// mid-work by a forced restart.

function setupAutoUpdater() {
  // Never run the updater when developing from source — only in the
  // actual installed/packaged app. Avoids dev-mode error spam.
  if (!app.isPackaged) return;

  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on('checking-for-update', () => {
    // Silent — no UI needed just for checking.
  });

  autoUpdater.on('update-not-available', () => {
    if (isManualUpdateCheck) {
      dialog.showMessageBox(mainWindow, {
        title: 'DericBI',
        message: "You're up to date.",
        detail: `You have the latest version (v${app.getVersion()}) of the DericBI desktop app.`,
      });
    }
    isManualUpdateCheck = false;
  });

  autoUpdater.on('update-available', async (info) => {
    const result = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Available',
      message: `DericBI v${info.version} is available.`,
      detail: 'You are currently on v' + app.getVersion() + '. Would you like to download it now?',
      buttons: ['Download Update', 'Not Now'],
      defaultId: 0,
      cancelId: 1,
    });
    if (result.response === 0) {
      autoUpdater.downloadUpdate();
    }
  });

  autoUpdater.on('download-progress', (progress) => {
    if (mainWindow) {
      mainWindow.setTitle(`DericBI — Downloading update... ${Math.round(progress.percent)}%`);
    }
  });

  autoUpdater.on('update-downloaded', async (info) => {
    if (mainWindow) mainWindow.setTitle('DericBI');
    const result = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Ready',
      message: `DericBI v${info.version} has been downloaded.`,
      detail: 'Restart now to install it, or install automatically the next time you quit.',
      buttons: ['Restart and Install', 'Later'],
      defaultId: 0,
      cancelId: 1,
    });
    if (result.response === 0) {
      autoUpdater.quitAndInstall(false, true);
    }
    // If "Later" — autoInstallOnAppQuit still installs it silently on next quit.
  });

  autoUpdater.on('error', (err) => {
    // Background checks fail silently (e.g. no internet) — only show an
    // error dialog if the user manually clicked "Check for Updates".
    if (isManualUpdateCheck) {
      dialog.showMessageBox(mainWindow, {
        type: 'error',
        title: 'Update Check Failed',
        message: 'Could not check for updates.',
        detail: String(err && err.message ? err.message : err),
      });
    }
    isManualUpdateCheck = false;
  });

  // Check once on startup (silent), then again every few hours in case the
  // app is left open for a long time.
  autoUpdater.checkForUpdates();
  setInterval(() => autoUpdater.checkForUpdates(), 4 * 60 * 60 * 1000);
}

function checkForUpdatesManually() {
  if (!app.isPackaged) {
    dialog.showMessageBox(mainWindow, {
      title: 'DericBI',
      message: 'Update checking is only available in the installed app, not in development mode.',
    });
    return;
  }
  isManualUpdateCheck = true;
  autoUpdater.checkForUpdates();
}

app.whenReady().then(() => {
  buildMenu();
  createWindow();
  setupAutoUpdater();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
