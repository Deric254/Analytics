---
title: DericBI Analytics
emoji: 📊
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# DericBI Analytics

This Space runs the DericBI analytics module (Dash app) using Docker.

## Local run

```bash
pip install -r requirements.txt
python app.py
```

Open `http://localhost:7860`.

## Notes

- Main entrypoint: `app.py`
- Dash server object exposed as: `server`
- Space runtime uses port `7860`

## Auto deploy from GitHub to Hugging Face Space

This repo includes a GitHub Actions workflow at `.github/workflows/sync-space.yml`.

To enable automatic deploy on every push to `main`:

1. Open your GitHub repository → **Settings** → **Secrets and variables** → **Actions**.
2. Add a new repository secret named `HF_TOKEN`.
3. Set the value to your Hugging Face token with **write** access.

After that, every `git push origin main` will automatically sync to:

- `https://huggingface.co/spaces/deric254/dericbi-analytics`
