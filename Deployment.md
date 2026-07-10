# Deploying the Garba 2026 Promo Dashboard on a VPS

A complete, start-to-finish guide to get the review dashboard running on your
VPS at `http://<your-vps-ip>:8412/dashboard`, surviving reboots, and
(optionally) served over HTTPS on your own domain.

This assumes a fresh **Ubuntu 22.04 / 24.04** VPS. Adjust package commands if
you use a different distro. Commands prefixed with `$` run as your normal user;
`sudo` is called out explicitly where root is needed.

---

## 0. What you need before starting

- SSH access to your VPS (e.g. `ssh youruser@207.180.235.87`).
- Your **Facebook Page ID** and a **long-lived Page Access Token**
  (see the main `README.md` section "Getting a Facebook Page Access Token").
- The `garba-promo-bot` project folder (this zip), ready to copy up.
- Decide on a **port** (default `8412`) and a **base path** (default
  `/dashboard`). Pick a port that nothing else on the VPS is using.

---

## 1. Install system dependencies

SSH into the VPS, then install Python, Node.js, and a couple of tools:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm git
```

Check versions (Node 18+ and Python 3.10+ are fine):

```bash
python3 --version
node --version
```

If your distro's `nodejs` is older than 18, install a current version:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

---

## 2. Copy the project to the VPS

From **your local machine** (not the VPS), from the folder containing the zip:

```bash
scp garba-promo-bot.zip youruser@207.180.235.87:~/
```

Then **on the VPS**, unzip it:

```bash
cd ~
unzip garba-promo-bot.zip -d garba-promo-bot
cd garba-promo-bot
```

(If the zip already contains the top-level folder, you'll end up with
`~/garba-promo-bot`. Adjust if your unzip nests it differently.)

---

## 3. Create your `.env` file

This holds your secrets and hosting config. Copy the example and edit it:

```bash
cp config/settings.example.env .env
nano .env
```

Fill in:

```
FB_PAGE_ID=your_real_page_id
FB_PAGE_ACCESS_TOKEN=your_real_long_lived_page_token
DASHBOARD_TOKEN=pick_a_shared_password_for_your_team
DASHBOARD_PORT=8412
DASHBOARD_BASE_PATH=/dashboard
```

- `DASHBOARD_TOKEN` is the password your team types once to access the
  dashboard. Choose something strong. (Leave it blank only if the VPS is on a
  private network no outsider can reach.)
- Change `DASHBOARD_PORT` if `8412` clashes with something.
- Save and exit nano with `Ctrl+O`, `Enter`, `Ctrl+X`.

Your `.env` is git-ignored and stays only on the VPS. Never share it.

---

## 4. Set your real event dates (optional but recommended)

Open `scripts/utils.py` and set the ticket dates so countdowns and
early-bird posts fire on the right days:

```bash
nano scripts/utils.py
```

```python
EARLY_BIRD_LAUNCH_DATE   = date(2026, 8, 1)    # your real ticket-open date
EARLY_BIRD_DEADLINE_DATE = date(2026, 9, 15)   # your real early-bird cutoff
```

---

## 5. Build and install everything

The included script installs backend dependencies and builds the React
frontend with the correct base path (read from your `.env`):

```bash
./deploy.sh
```

If you get a permissions error, make it executable first:

```bash
chmod +x deploy.sh
./deploy.sh
```

When it finishes, it prints the exact command to run the dashboard.

---

## 6. First run (test it works)

Start the server manually to confirm everything's wired up:

```bash
cd backend
DASHBOARD_BASE_PATH=/dashboard uvicorn app:app --host 0.0.0.0 --port 8412
```

Leave it running, and from your browser open:

```
http://207.180.235.87:8412/dashboard
```

You should see the login screen. Enter your `DASHBOARD_TOKEN`, then the review
dashboard. Click **Pull due posts** to load anything scheduled for today.

Press `Ctrl+C` in the terminal to stop it once you've confirmed it loads.

> If it doesn't load, check the two most common causes first: (a) the port is
> blocked by a firewall — see step 8; (b) `DASHBOARD_BASE_PATH` used at build
> time (step 5) doesn't match the one used at run time. Re-run `./deploy.sh`
> after changing `.env` to keep them in sync.

---

## 7. Keep it running with systemd (survives reboots & logout)

Running uvicorn by hand stops the moment you close SSH. To run it as a proper
background service, create a systemd unit.

First, find your project's absolute path and your username:

```bash
pwd        # e.g. /home/youruser/garba-promo-bot
whoami     # e.g. youruser
```

Create the service file:

```bash
sudo nano /etc/systemd/system/garba-dashboard.service
```

Paste this, replacing `youruser` and the paths with your real values:

```ini
[Unit]
Description=Garba 2026 Promo Review Dashboard
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/garba-promo-bot/backend
EnvironmentFile=/home/youruser/garba-promo-bot/.env
ExecStart=/usr/bin/uvicorn app:app --host 0.0.0.0 --port 8412
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> Note: `EnvironmentFile` loads your `.env`, so `DASHBOARD_BASE_PATH` and the
> Facebook token are available to the service. If you changed the port in
> `.env`, change it in `ExecStart` here too.

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable garba-dashboard
sudo systemctl start garba-dashboard
```

Check it's running:

```bash
sudo systemctl status garba-dashboard
```

Useful commands later:

```bash
sudo systemctl restart garba-dashboard    # after code/config changes
sudo systemctl stop garba-dashboard
journalctl -u garba-dashboard -f          # live logs
```

---

## 8. Open the firewall port

If your VPS uses `ufw`, allow the port:

```bash
sudo ufw allow 8412/tcp
sudo ufw reload
```

Some providers (Contabo, Hetzner, AWS, etc.) also have a **separate firewall in
their web control panel** — open the port there too if the browser still can't
reach it.

---

## 9. Automate the daily queue fill (cron or Hermes)

The dashboard shows posts once they're pulled from the schedule. To fill the
queue automatically each day, point your scheduler at the wrapper script.

**With cron:**

```bash
crontab -e
```

Add (adjust the path):

```
0 9 * * * /home/youruser/garba-promo-bot/scripts/run_scheduler.sh
```

That runs every day at 09:00 server time and enqueues anything due. It does
**not** post anything — posting only happens when a team member approves in the
dashboard.

**With Hermes:** give it the same command,
`/home/youruser/garba-promo-bot/scripts/run_scheduler.sh`, on whatever schedule
you prefer.

---

## 10. (Optional) HTTPS on your own domain with nginx

Serving over `http://ip:port` works, but for a clean `https://yourdomain.com/dashboard`
URL, put nginx in front.

Install nginx and Certbot:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Point your domain's DNS **A record** at your VPS IP first, then create an nginx
site config:

```bash
sudo nano /etc/nginx/sites-available/garba
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /dashboard {
        proxy_pass http://127.0.0.1:8412;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it and reload nginx:

```bash
sudo ln -s /etc/nginx/sites-available/garba /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Add HTTPS automatically:

```bash
sudo certbot --nginx -d yourdomain.com
```

Now the dashboard is at `https://yourdomain.com/dashboard`, and you can close
the raw port `8412` on the firewall so it's only reachable through nginx:

```bash
sudo ufw delete allow 8412/tcp
```

---

## Updating the app later

When you change code, captions, or the schedule:

```bash
cd ~/garba-promo-bot
# (copy up new files, or edit in place)
./deploy.sh                              # rebuild frontend if it changed
sudo systemctl restart garba-dashboard   # pick up backend changes
```

Adding photos: drop them into `content/media/` — no rebuild needed, they appear
in the dashboard's background-photo dropdown on the next page load.

---

## Quick troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Browser can't connect | Firewall — open the port (step 8), check provider panel firewall too. |
| Page loads but assets 404 | Build base path ≠ run base path. Re-run `./deploy.sh` after editing `.env`. |
| "Address already in use" on start | Another process uses the port. Pick a new `DASHBOARD_PORT` in `.env` + the systemd `ExecStart`. |
| Login rejects token | `DASHBOARD_TOKEN` in `.env` doesn't match what you typed. Restart service after editing `.env`. |
| Approve fails with a Facebook error | Token expired or missing permission. Regenerate the long-lived Page token (see main README). |
| Service won't start | `journalctl -u garba-dashboard -f` shows the real error. Usually a path typo in the unit file. |

---

## Security checklist

- Keep `.env` private; never commit it or paste the token anywhere.
- Set a strong `DASHBOARD_TOKEN` — anyone with it can post to your Page.
- Prefer the nginx + HTTPS setup (step 10) over raw `http://ip:port` for
  anything beyond quick testing.
- Consider restricting the port to known IPs if only a few people need access.