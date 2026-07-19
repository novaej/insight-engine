# Usage Guide (for when you've forgotten how this works)

The everyday workflow, in the order you'll actually use it. Two ideas to hold onto:

- **The watchdog is automatic and free.** A GitHub Actions cron re-analyzes your
  holdings daily (deterministic, no AI) and emails you what changed. You don't run
  anything for this.
- **The AI "deep read" is manual and costs a little.** You run the full analyze
  when *you* want the written explanations, alternatives, and exposure breakdown.

Set these once for the snippets below (use your deployed URL, or `http://localhost:8000` locally):

```bash
BASE=https://insight-engine-staging.onrender.com
TOKEN=$(curl -s -X POST $BASE/login -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"…"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
AUTH="Authorization: Bearer $TOKEN"; JSON="Content-Type: application/json"
```
(Tokens rotate on every login — re-run this when yours stops working.)

## 1. One-time setup

Register once, then add your holdings. Each add is a **lot**, so buying the same
ticker twice at different prices is two adds:

```bash
curl -X POST $BASE/users -H "$JSON" -d '{"email":"you@example.com","password":"…","name":"You"}'

curl -X POST $BASE/portfolio/positions -H "$AUTH" -H "$JSON" \
  -d '{"ticker":"AAPL","quantity":2,"purchase_price":180,"purchase_date":"2025-11-02"}'
curl -X POST $BASE/portfolio/positions -H "$AUTH" -H "$JSON" \
  -d '{"ticker":"VOO","quantity":1,"purchase_price":500}'
```

Then run one full analysis with AI to seed rich insights (and set your profile):

```bash
curl -X POST $BASE/portfolio/analyze -H "$AUTH" -H "$JSON" \
  -d '{"user_profile":{"risk":"moderate","horizon":"long","goal":"growth"},"use_ai":true}'
```
Omitting `assets` analyzes your stored positions. Not sure how to phrase your
profile? `POST /profile/interpret` turns plain words into `{risk,horizon,goal}` you
can review and pass here.

## 2. Every day — nothing to do

The watchdog runs on its schedule and **emails you only when something changed** —
grouped into "Positive moves" (breakouts, upgrades, health rising) and "Potential
concerns" (downgrades, health drops, price falling below its 200-day average, new
news flags). The first run per holding is a silent baseline; alerts start the next
day.

If you never run a manual analyze, the watchdog still tracks everything — it just
stores insights **without** the AI narrative, alternatives, or position weights.

## 3. When you want the full picture — run analyze with AI

Do this occasionally (e.g. weekly, or when an alert catches your eye):

```bash
curl -X POST $BASE/portfolio/analyze -H "$AUTH" -H "$JSON" \
  -d '{"user_profile":{"risk":"moderate","horizon":"long","goal":"growth"},"use_ai":true}'
```
This is the only routine action that spends OpenAI credit (one batched call for the
whole portfolio). Add `"language":"es"` to get the AI text translated.

## 4. When you buy or sell

Just update your positions — **you don't need to re-run analyze** for the watchdog
to notice; it reads your current positions every run.

```bash
# bought something new
curl -X POST $BASE/portfolio/positions -H "$AUTH" -H "$JSON" \
  -d '{"ticker":"NVDA","quantity":0.5,"purchase_price":140}'

# sold a holding (get its lot id from GET /portfolio/positions)
curl -X DELETE $BASE/portfolio/positions/123 -H "$AUTH"
```
A newly added ticker gets a silent baseline on its first watchdog run, then is
tracked. A sold ticker drops out of monitoring (its past insights stay in history).

## 5. Refresh just one holding

Cheaper than re-analyzing everything when you only care about one asset:

```bash
curl -X POST $BASE/portfolio/positions/AAPL/analyze -H "$AUTH" -H "$JSON" \
  -d '{"use_ai":true}'
```
Uses your saved profile, appends to history. (Portfolio weight/concentration are
skipped here — those need the whole portfolio; use the full analyze for them.)

## 6. Checking on things

```bash
curl $BASE/portfolio -H "$AUTH"                       # holdings + latest insight per ticker
curl "$BASE/insights?ticker=AAPL&limit=10" -H "$AUTH" # how AAPL's state/scores moved over time
```
Note: after a nightly watchdog run, the "latest insight" is the no-AI version.
Run a manual analyze to bring the AI narrative back to the top; the older AI
insights remain in history.

## 7. Managing alerts & manual sweeps

```bash
curl -X PATCH $BASE/users/me -H "$AUTH" -H "$JSON" -d '{"alerts_enabled":false}'  # pause emails
```
Force a sweep without waiting for the cron: GitHub → **Actions → Monitoring → Run
workflow**. The daily schedule and time live in `.github/workflows/monitoring.yml`
(`cron:`, in **UTC**).

---

**Cost recap:** the watchdog and all position/portfolio bookkeeping are free.
OpenAI is charged only when you run analyze (or single-asset analyze) with
`use_ai: true`. Azure translation only when you pass `language`. Render + Neon +
GitHub Actions stay within free tiers for personal use.

See `api_reference.md` for the full endpoint list and `DEPLOY.md` for the
deploy/monitoring setup.
