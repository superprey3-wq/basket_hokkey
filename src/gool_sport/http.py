from __future__ import annotations
import json
import urllib.request
from typing import Any

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36"

def get_text(url: str, *, headers: dict[str,str] | None=None, timeout: float=10.0) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":UA,**(headers or {})})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return response.read().decode("utf-8",errors="replace")
    except Exception:
        return ""

def get_json(url: str, *, headers: dict[str,str] | None=None, timeout: float=8.0) -> dict[str,Any] | None:
    body=get_text(url,headers=headers,timeout=timeout)
    if not body:
        return None
    try:
        value=json.loads(body)
        return value if isinstance(value,dict) else None
    except Exception:
        return None
