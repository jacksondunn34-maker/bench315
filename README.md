# Bench 315 — cloud setup (free, phone-only)

This makes your bench app fully hands-off: every morning a free GitHub job logs into
Garmin, pulls your Training Readiness + sleep + resting HR, and publishes it to a web
page you keep on your iPhone home screen. You just wake up and open it.

**How it works (plain version):**
- **GitHub Actions** = a free robot that runs `update.py` once a day with full internet access.
- `update.py` logs into Garmin, grabs your numbers, and saves `data/today.json`.
- **GitHub Pages** = a free, always-on website that serves `index.html` (your app).
- Your phone opens that page and reads `today.json` — the workout is already adjusted.

No computer of yours has to be on. Total cost: $0.

---

## One-time setup (about 15 minutes, all in a web browser)

### 1. Make a GitHub account
Go to https://github.com and sign up (free) if you don't have one.

### 2. Create a repository
- Click the **+** (top right) → **New repository**.
- Name it `bench315`. Set it to **Public**. Click **Create repository**.

### 3. Upload these files
- On the new repo page, click **Add file → Upload files**.
- Drag in **everything inside the `bench315-cloud` folder** — including the `data` folder
  and the hidden `.github` folder. (On Mac, press **Cmd+Shift+.** in Finder to see the
  `.github` folder, then drag it in too.)
- The structure in the repo must look like:
  ```
  index.html
  manifest.webmanifest
  service-worker.js
  icon-180.png  icon-192.png  icon-512.png
  update.py
  requirements.txt
  data/today.json
  .github/workflows/daily.yml
  ```
- Click **Commit changes**.

### 4. Add your Garmin login as secrets
- In the repo: **Settings → Secrets and variables → Actions → New repository secret**.
- Add two secrets:
  - Name `GARMIN_EMAIL`, value = your Garmin Connect email.
  - Name `GARMIN_PASSWORD`, value = your Garmin Connect password.
- (Secrets are encrypted and only used by the daily job. They are never shown on the site.)

### 5. Turn on GitHub Pages
- **Settings → Pages**.
- Under **Build and deployment → Source**, pick **Deploy from a branch**.
- Branch: **main**, folder: **/ (root)**. Click **Save**.
- After a minute it shows your site URL, like:
  `https://YOURNAME.github.io/bench315/`

### 6. Run the daily job once now (to test)
- Go to the **Actions** tab → click **Daily Garmin pull** → **Run workflow**.
- Wait ~1 minute. Open it and check it's green. Then open `data/today.json` in the repo —
  it should now show your real Garmin numbers and today's date.
- If it fails, click the run to read the log. Most common cause: a typo in the email/password
  secret, or Garmin temporarily asking for a re-login (just run it again).

### 7. Add it to your iPhone home screen
- On your iPhone, open the Pages URL (step 5) in **Safari**.
- Tap the **Share** button → **Add to Home Screen** → **Add**.
- You now have a "Bench 315" app icon. Open it each morning — readiness is already loaded.

### 8. Set the run time to your timezone
- Open `.github/workflows/daily.yml` in the repo (pencil icon to edit).
- The line `cron: "40 11 * * *"` is in **UTC**. `11:40 UTC` ≈ 6:40 AM US Central.
  Change the hour for your zone: Eastern ≈ `40 10`, Mountain ≈ `40 12`, Pacific ≈ `40 13`.
- Commit the change.

---

## Good to know
- **Timing:** GitHub's free scheduler usually runs within a few minutes of the set time, but
  can occasionally be delayed 15–30 min at busy hours. Your readiness still lands well before
  most training. You can always hit **Run workflow** manually.
- **Keep it active:** GitHub pauses scheduled jobs if a repo has no activity for 60 days. The
  daily commit keeps it alive, so this won't be an issue while you're using it.
- **Garmin login:** this uses an unofficial login (the only option Garmin offers individuals).
  It's reliable but not guaranteed — if Garmin changes something, the job may need a quick fix.
  Keep **two-factor auth off** on Garmin for the automated login to work.
- **Your data stays yours:** everything lives in your own GitHub repo. Workout check-offs and
  food logs are stored on your phone (in the app), not uploaded anywhere.

## Changing your program
The whole training program lives in `index.html` (search for `buildWeek`). Weights, weeks,
exercises, and the readiness-adjustment rules are all there. Ask Claude to edit it and re-upload.
