# Dezee Forex YouTube Automation

Automated daily COT (Commitment of Traders) contrarian forex content for YouTube.

## What it does

Every day at 6 AM UTC, GitHub Actions:
1. Fetches the latest CFTC COT report for 7 major forex pairs
2. Generates a video script using Claude AI (COT contrarian angle)
3. Renders a long-form video + YouTube Short (slideshow + AI voiceover)
4. Uploads both to YouTube automatically

## Required GitHub Secrets

Set these in **Settings → Secrets → Actions**:

| Secret | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `ELEVENLABS_API_KEY` | elevenlabs.io (free tier ok) |
| `PEXELS_API_KEY` | pexels.com/api |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN` | Run `scripts/get_youtube_token.py` |

## Manual trigger

Go to **Actions → Daily Forex YouTube Video → Run workflow**

## Strategy

COT Contrarian: When large speculators are heavily positioned one way, fade them by following the commercials (banks/hedgers). Extreme net positioning = high-probability reversal setup.
