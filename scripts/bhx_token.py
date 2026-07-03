#!/usr/bin/env python3
"""Mint a short-lived Bách Hóa Xanh API token + deviceid with headless Chromium.

The BHX API (apibhx.tgdd.vn) needs an `Authorization: Bearer <token>` header that
the site's own JS mints per session. We open the site once, let it fire its
internal API calls, and intercept the auth header off one of them. `deviceid`
comes from the `ck_bhx_us_log` cookie (`.did`) or a generated UUID.

SKELETON — verify selectors/cookie/name at PoC (see docs/research/POC-FINDINGS.md).
Chromium is pre-installed at /opt/pw-browsers/chromium (do NOT run playwright
install). Usage:  python scripts/bhx_token.py  -> prints JSON {token, deviceid}
"""
import asyncio
import json
import uuid

BHX_HOME = "https://www.bachhoaxanh.com/"
TRIGGER_SUBSTRINGS = ("Menu/GetMenuV2", "Location/V2/GetStoresByLocation")
DEVICE_COOKIE = "ck_bhx_us_log"


async def mint() -> dict:
    from playwright.async_api import async_playwright  # imported lazily

    token = None
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path="/opt/pw-browsers/chromium"
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()

        def on_request(req):
            nonlocal token
            if any(s in req.url for s in TRIGGER_SUBSTRINGS):
                auth = req.headers.get("authorization")
                if auth:
                    token = auth

        page.on("request", on_request)
        await page.goto(BHX_HOME, wait_until="networkidle", timeout=60_000)
        # Give the SPA a moment to fire its internal calls.
        await page.wait_for_timeout(4_000)

        deviceid = None
        for c in await ctx.cookies():
            if c["name"] == DEVICE_COOKIE:
                try:
                    deviceid = json.loads(c["value"]).get("did")
                except Exception:
                    deviceid = None
                break
        await browser.close()

    return {"token": token, "deviceid": deviceid or str(uuid.uuid4())}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(mint())))
