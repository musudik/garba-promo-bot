# Garba 2026 Promo Bot + Review Dashboard

Social media automation for **Europe's Biggest Sharad Purnima Raas Garba 2026**
(Apexa Pandya live, 25 Oct 2026) — with a **human-in-the-loop review dashboard**.
Nothing posts to Facebook until a team member approves it.

## What it does

1. A scheduler (cron / Hermes) reads `content/schedule.csv` and drops any posts
   due that day into a **review queue** — it does not post anything itself.
2. Your team opens the **dashboard** (React app served by the backend), sees each
   pending post as a card with its generated image + caption, and can **edit the
   text, swap the background photo, regenerate the image, then approve or reject**.
3. On **Approve**, the backend posts it to your Facebook Page. The access token
   lives only on the server — it's never sent to the browser.

You can also create one-off posts directly in the dashboard ("New post"), on top
of whatever the schedule queues.

## Images without AI generation

The recurring, data-driven posts (countdown, early bird, selling fast, sponsor
spotlight, food stalls, sponsorship-open) are drawn programmatically by
`scripts/image_overlay.py` — a fixed branded template (the flyer's black/gold
look) with the headline/subtext plugged in. No AI image generation, no
per-post design work, always on-brand. For artist/venue/food photo posts, it
uses the real photos and videos you drop into `content/media/`. Any generated
graphic can also use a real photo as its backdrop (a dark overlay keeps text
readable) — pick it in the dashboard's "Background photo" dropdown.

## Architecture (why it's all on the VPS)

GitHub Pages can only serve static files — it can't run the posting logic,
generate images, or hold your Facebook token. So the whole thing runs on your
VPS as one app: a FastAPI backend that also serves the built React frontend
(single origin, one deploy, token stays server-side). You open it at
`http://<your-vps>:8000`.

```
scheduler (cron/Hermes) --> review queue (content/queue.json)
                                   |
                          FastAPI backend (backend/app.py) --> Facebook Graph API
                                   |  serves
                          React dashboard (frontend/dist)  <-- your team reviews
```

## Setup on your VPS

1. Copy this folder to the VPS.
2. Create `.env` in the project root (copy from `config/settings.example.env`):
   ```
   FB_PAGE_ID=your_page_id
   FB_PAGE_ACCESS_TOKEN=your_long_lived_page_token
   DASHBOARD_TOKEN=some_shared_password    # team login; omit to disable auth on a private network
   ```
3. Build + install everything:
   ```
   ./deploy.sh
   ```
4. Run the dashboard (port + base path come from .env):
   ```
   cd backend && DASHBOARD_BASE_PATH=/dashboard uvicorn app:app --host 0.0.0.0 --port 8412
   ```
   Open `http://<your-vps-ip>:8412/dashboard`. The port (8412) and path
   (/dashboard) are configurable in .env via DASHBOARD_PORT and
   DASHBOARD_BASE_PATH — 8412 is chosen to avoid clashing with common ports
   like 3000/8000/8080. Visiting the bare `/` or `:8412` redirects to the
   dashboard. **In production, put it behind HTTPS and a firewall** (nginx
   reverse proxy + your domain). For a long-running service, run uvicorn under
   systemd or pm2.
5. Wire up the daily queue fill — point Hermes (or cron) at:
   ```
   /full/path/to/garba-promo-bot/scripts/run_scheduler.sh
   ```
   See `crontab.example.txt`. Safe to run often; it only queues what's due.

## Using the dashboard

- **To Review** tab: pending posts. Edit headline/subtext, pick a background
  photo, **Regenerate image** to preview changes, then **Approve & post** or
  **Reject**. Editing the caption is free-text.
- **Pull due posts**: manually fill the queue from the schedule right now.
- **New post**: compose a one-off for review.
- **Approved / Posted / Rejected** tabs: history.

## Content plan shipped in schedule.csv

A ~3-month plan is pre-loaded, event-focused rather than generic:

- **Phase 1 (now -> early bird launch)**: countdown graphics + artist, venue, and
  food-stall teasers.
- **Early bird launch**: "Early bird is live" + "selling fast" urgency posts.
- **Sponsors / open-for-marketing** (parallel): "Partner with us", "Be seen by
  5000+", and sponsor spotlight posts.
- **Early bird deadline**: "5 days left", "last chance", "ends tonight".
- **Final countdown**: weekly days-to-go posts up to event day.

`{days_left}` is computed at post time so countdowns are always accurate.
Ticket dates are placeholders in `scripts/utils.py`
(`EARLY_BIRD_LAUNCH_DATE`, `EARLY_BIRD_DEADLINE_DATE`) — set your real dates
there. Sponsor names, cities, etc. can be edited per-post in the dashboard, or
set in the schedule's `extra` column (e.g. `sponsor_name=Starvent`).

## Getting a Facebook Page Access Token

1. developers.facebook.com/apps -> **Create App** -> **Other** -> **Business**.
2. **Settings > Basic**: note your **App ID** and **App Secret**.
3. **Tools > Graph API Explorer**: select your app, "Get User Access Token", add
   permissions `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
   `business_management` -> Generate, and grant your Page.
4. Exchange the short-lived token for a long-lived one:
   ```
   https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}
   ```
5. Get your Page ID + long-lived Page token:
   ```
   https://graph.facebook.com/v20.0/me/accounts?access_token={long-lived-user-token}
   ```
   Use the `id` and `access_token` from your Page in `.env`.

Treat the token like a password — it only belongs in `.env` on your VPS (which
`.gitignore` keeps out of version control).

## Instagram (optional)

Set a post's `platform` to `instagram`. IG needs a public media URL (it can't
take direct uploads), so serve `content/media/` behind a public URL and use that
in the background/media field. Facebook is the simpler default.

## Files

```
backend/
  app.py              - FastAPI: review queue API + posting + serves frontend
  queue_store.py      - JSON-backed review queue, schedule.csv ingestion
  requirements.txt
frontend/
  src/App.jsx         - review dashboard UI
  src/api.js          - API client
  src/styles.css      - festival black/gold theme
  dist/               - built app (created by deploy.sh / npm run build)
scripts/
  image_overlay.py    - programmatic branded image generator (no AI)
  facebook_api.py     - Facebook Graph API wrapper
  instagram_api.py    - Instagram Graph API wrapper (optional)
  post_scheduler.py   - enqueues due posts for review (run by cron/Hermes)
  run_scheduler.sh    - wrapper for cron/Hermes
  utils.py            - event date, ticket dates, cities, templating
content/
  schedule.csv        - the content plan
  captions/templates/ - caption templates ({city}, {days_left}, {event_date})
  media/              - your photos & videos (+ flyer_main.jpg)
  generated/          - auto-rendered preview images
  queue.json          - the live review queue (created at runtime)
deploy.sh             - build frontend + install backend
crontab.example.txt   - sample scheduler lines
config/settings.example.env
```
