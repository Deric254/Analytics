Put your app icon here as icon.ico before building.

Requirements for a Windows .ico file:
- Must be a real .ico file (not a renamed .png)
- Recommended: 256x256px, containing multiple sizes embedded (16, 32, 48, 256)

Free way to make one:
1. Get or create a square PNG logo (your DericBI logo works — download from
   https://dericbi.vercel.app/assets/img/logo.png)
2. Convert it at https://icoconvert.com or https://convertio.co/png-ico/
3. Save the result here as: build/icon.ico

Until this file exists, electron-builder will use its own default icon —
the build will still work, it just won't look branded.
