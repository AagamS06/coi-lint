"""Optional Slack notification through an incoming webhook (free; you create it in your own workspace).

The webhook URL is a secret, so coi-lint only reads it from an environment variable you name
(e.g. --slack-env SLACK_WEBHOOK_URL) and never writes it anywhere.
"""

from __future__ import annotations

import json
import os
import urllib.request


def webhook_from_env(var: str) -> str:
    url = os.environ.get(var, "").strip()
    if not url:
        raise ValueError(f"environment variable {var} is not set (it should hold your Slack webhook URL)")
    if not url.startswith("https://"):
        raise ValueError(f"{var} must be an https:// webhook URL")
    return url


def post_slack(url: str, text: str, timeout: float = 10.0) -> None:
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status >= 300:
            raise ValueError(f"Slack webhook returned HTTP {resp.status}")
