#!/usr/bin/env bash
# One-command weekly run FROM A RESIDENTIAL IP (home machine).
# Crawls BHX (needs a home IP) + WinMart, renders the static site, commits & pushes.
# See docs/LOCAL-RUN.md for setup. Safe to re-run — the crawlers overwrite each
# chain's current price and build_run is idempotent for the week's history rows.
set -uo pipefail

BRANCH="${GIACHO_BRANCH:-claude/website-design-docs-plan-v1ljj3}"
PROVINCE="${BHX_PROVINCE:-3}"
STORE="${BHX_STORE:-2546}"
cd "$(dirname "$0")/.."

echo "▶ Giá Chợ weekly local run — branch $BRANCH"
git fetch origin "$BRANCH" >/dev/null 2>&1 && git checkout "$BRANCH" >/dev/null 2>&1
git pull --ff-only origin "$BRANCH" >/dev/null 2>&1 || echo "  (pull skipped)"

echo "▶ 1/3  BHX (residential IP)…"
if python3 scripts/crawl_bhx.py --province "$PROVINCE" --store "$STORE"; then
  echo "  BHX ok"
else
  echo "  ⚠ BHX step failed (blocked IP? stale token? wrong store/slugs) — continuing WinMart-only."
  echo "    Tip: run 'python3 scripts/crawl_bhx.py --dump' to inspect the live response."
fi

echo "▶ 2/3  WinMart…"
python3 scripts/crawl_winmart.py || { echo "WinMart crawl failed"; exit 1; }

echo "▶ 3/3  Render site + extend history…"
python3 scripts/build_run.py

WEEK="$(python3 -c "import json;print(json.load(open('data/db/meta.json'))['last_run_week'])")"
git add -A
if git diff --cached --quiet; then
  echo "▶ nothing changed — done."
  exit 0
fi
git commit -q -m "data: weekly update ${WEEK}"
n=0
until git push -u origin "$BRANCH"; do
  n=$((n+1)); [ "$n" -ge 4 ] && { echo "push failed after retries"; exit 1; }
  s=$((2**n)); echo "  retry $n in ${s}s"; sleep "$s"
done
echo "▶ done — pushed ${WEEK}. GitHub Pages will redeploy."
