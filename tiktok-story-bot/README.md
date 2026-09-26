# TikTok Story Bot

Makes Reddit-style story videos (a post-title card, then big word-by-word captions with a narrator voice over background footage) and posts them to your TikTok account through TikTok's official Content Posting API. It runs for free on GitHub Actions, twice a day by default.

```
stories/*.txt  ─┐
  or Claude AI ─┴─> voice (edge-tts) ─> captions + title card ─> ffmpeg video ─> TikTok upload
```

## Setup (about 30 minutes, once)

### 1. Put the code on GitHub
Create a **private** GitHub repo and upload everything in this folder (keep the `.github` folder).

### 2. Create a TikTok developer app
1. Log in at https://developers.tiktok.com and click **Manage apps → Connect an app**.
2. Add the products **Login Kit** and **Content Posting API**. In Content Posting API, turn on **Direct Post**.
3. Scopes: `user.info.basic` and `video.publish`.
4. Under Login Kit, add a **Redirect URI**. It must be an `https://` address you control. The page doesn't need to do anything, because you only copy the address out of the browser bar. A free GitHub Pages address such as `https://YOURNAME.github.io/` works.
5. Copy the **Client key** and **Client secret**.

> **Important:** until TikTok **audits** your app, uploads only work to a **private** TikTok account and are posted as "Only me". To post publicly, submit the app for audit on the Content Posting API page. Until it's approved, set your account to private, and open each video in the TikTok app to make it public yourself.

### 3. Connect your TikTok account (one time)
On any computer with Python 3.10+ and ffmpeg (a GitHub Codespace on your repo works too):
```bash
pip install -r requirements.txt
cp .env.example .env        # fill in TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI
python main.py auth
```
Open the link it prints, approve, then paste the address you land on. It prints a `TIKTOK_REFRESH_TOKEN`.

### 4. Add GitHub secrets
Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `TIKTOK_CLIENT_KEY` | from step 2 |
| `TIKTOK_CLIENT_SECRET` | from step 2 |
| `TIKTOK_REFRESH_TOKEN` | from step 3 |
| `GH_PAT` | a [fine-grained token](https://github.com/settings/personal-access-tokens/new) for this repo with **Secrets: Read and write**. The bot uses it to save TikTok's renewed login automatically. |
| `ANTHROPIC_API_KEY` | *(optional)* lets the bot write new stories when your queue is empty |

Optional **Variables** tab: `PRIVACY_LEVEL`, `HASHTAGS`, `STORY_SOURCE` (`queue`, `ai` or `auto`).

### 5. Add background footage
Put one or more vertical or horizontal `.mp4` files in `backgrounds/`. Each file must be under 100 MB for GitHub. Every video uses a random section of a random file. Use footage you have the rights to, such as your own gameplay recordings or royalty-free stock. Re-uploading other creators' clips can get videos muted or taken down. With no footage, the bot uses an animated gradient.

### 6. Add stories
Each story is a `.txt` file in `stories/`. The first line is the title and the rest is the story. Files post in alphabetical order (`001-...`, `002-...`) and move to `stories/done/` after posting. Aim for 180–260 words, about 1–1.5 minutes of narration.

Put a line `#ai` in a file if the story was AI-written, so TikTok labels it. Stories the bot writes with Claude are labeled automatically.

### 7. Run it
Repo → **Actions → Post TikTok story → Run workflow**. After that, it runs on the schedule in `.github/workflows/post.yml` (11am and 7pm New York time). Each run's video is also saved under the run's **Artifacts** for 7 days.

## Commands (local / on your server)
```bash
pip install -r requirements.txt      # first time only
cp .env.example .env                 # fill in your API keys

python main.py make                  # build a video into output/ without posting
python main.py post                  # build and post to TikTok
python main.py upload output/x.mp4   # post a video you already made
python main.py make --offline-voice  # test the pipeline with a placeholder voice (no network needed)
```

## Good to know
- **Voice service:** the narrator uses Microsoft's free Edge neural voices via `edge-tts`. Install it locally with `pip install edge-tts`. For testing without internet, use `--offline-voice`. The service is free and doesn't require a key.
- **Rate limits:** TikTok caps how many API posts one account can make per day (an error `spam_risk_too_many_posts` means you hit it). 1–3 a day is a sensible pace.
- **Real Reddit posts:** the bot doesn't scrape Reddit. Reading real people's posts word for word raises copyright and Reddit-terms problems, and TikTok's originality rules push down re-uploaded content. Write your own stories, heavily rework them, or let the AI mode write original ones.
- **Change the voice:** set `TTS_VOICE`, for example `en-US-AriaNeural`, `en-US-GuyNeural`, `en-GB-RyanNeural`, or `en-AU-NatashaNeural`. See all [Edge TTS voices](https://github.com/rany2/edge-tts/blob/master/VOICES.md).
- **Custom font:** drop a `.ttf` into a `fonts/` folder and set `FONT_NAME` to its family name.
