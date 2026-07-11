# DericBI Desktop App

A native Windows wrapper around your live DericBI deployment at
`https://dericbi-analytics.onrender.com`, with real app-style auto-updates —
like Chrome, Slack, or VS Code — for the desktop shell itself.

This folder is completely isolated from the web app. Render only reads
`Dockerfile` / `requirements.txt` / `app.py` etc. at the repo root — it
never looks inside `desktop/`, so nothing here affects your live deployment.

---

## Two different kinds of "update" — worth understanding

**1. Content updates (pages, features, AI, reports, everything you build in
Python)** — these need **no installer update at all**. The desktop app is a
window pointed at your live Render URL, so the moment you push to the web
app and Render redeploys, every open DericBI window shows the change on
next reload. This is instant and automatic already.

**2. Shell updates (the desktop wrapper itself — window size, menu bar,
icon, the update-checker code)** — these DO need a new installer, and DO
need real auto-update, which is what this section covers. You'll rebuild
the installer far less often than you update the web app.

---

## How the auto-update actually works

The app checks GitHub Releases automatically:
- Once when it starts
- Every 4 hours if left open

If a newer version is found, the exact flow is:

1. **"v1.0.1 is available. Download Update?"** — user chooses Download or
   Not Now. Nothing downloads without this click.
2. Downloads in the background. Window title shows progress.
3. **"v1.0.1 downloaded. Restart and Install?"** — user chooses to install
   now, or Later.
4. If Later — it still installs silently the next time they quit the app,
   so they're never stuck on an old version, but never interrupted
   mid-work by a forced restart either.

Users (or you) can also trigger a check any time via the menu:
**DericBI → Check for Updates...**

Background checks fail silently if there's no internet. A manual check
shows a clear error if something's actually wrong.

---

## One-time setup required before this works

Open `desktop/package.json` and replace these two placeholders with your
real GitHub username and repo name:

```json
"publish": {
  "provider": "github",
  "owner": "REPLACE_WITH_YOUR_GITHUB_USERNAME",
  "repo": "REPLACE_WITH_YOUR_REPO_NAME"
}
```

That's the only manual step, ever. Everything else — building, tagging,
publishing, and users receiving the update — is automatic from here on.

---

## Releasing a new desktop version

1. Bump the version number in `desktop/package.json`:
   ```json
   "version": "1.0.1"
   ```
2. Push to `main`

That's it. GitHub Actions then automatically:
- Builds the Windows installer
- Creates a git tag and GitHub Release (`v1.0.1`)
- Uploads the installer **and** the `latest.yml` file that the auto-updater
  reads to detect new versions

Every installed copy of DericBI checks in within a few hours (or
immediately if the user reopens the app) and offers the update.

No manual "Run workflow" click, no artifact downloading, no manual release
creation — push is the only action needed.

---

## Getting the very first installer

For the very first install (before anyone has the app yet), download it
from your repo's **Releases** page after the first successful build:
`https://github.com/<your-username>/<your-repo>/releases`

Grab the `.exe` from the latest release and share that link with your
first users. Every install after that updates itself.

---

## Building locally instead (optional)

Requires Node.js 20+ (https://nodejs.org).

```
cd desktop
npm install
npm run build:win        # build only, no publish
npm run publish:win      # build AND publish to GitHub (needs GH_TOKEN env var)
```

---

## Before your first build

Add a proper icon — see `build/ICON_README.txt` for instructions. Without
one, the build still works, it just uses Electron's default icon.

---

## What users experience

1. Download and run the `.exe` from Releases (first time only)
2. Standard Windows installer — choose install location, creates a Start
   Menu and Desktop shortcut named "DericBI"
3. Opens a native window showing the live DericBI app
4. Menu bar: Reload, Check for Updates, Open in Browser, About, standard
   Edit/View options
5. If the internet is down or Render is waking up from idle (free tier cold
   start), a friendly "DericBI is unreachable" screen appears with a Reload
   button — never a blank white screen
6. From here on, update prompts appear automatically when a new shell
   version is published — no need to revisit the Releases page
