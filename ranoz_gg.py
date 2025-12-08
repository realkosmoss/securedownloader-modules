from patchright.sync_api import sync_playwright
from curl_cffi import requests
import re

def _find_href(obj):
    if isinstance(obj, dict):
        if "href" in obj:
            return obj["href"]
        for v in obj.values():
            href = _find_href(v)
            if href:
                return href
    elif isinstance(obj, list):
        for item in obj:
            href = _find_href(item)
            if href:
                return href
    return None

def ranoz_gg_fetch(session: requests.Session, url: str) -> str:
    resp = session.get(url)
    text = resp.text

    try:
        text_decoded = text.encode().decode('unicode_escape')
    except:
        text_decoded = text

    match_fake = re.search(r'"directLink":"(https://[^"]+)"', text_decoded)
    fake_link = match_fake.group(1) if match_fake else None

    match_real = re.search(r'"href":"(https://st\d+\.ranoz\.gg/[^"]+)"', text_decoded)
    real_link = match_real.group(1) if match_real else None

    if not fake_link and not real_link:
        print("[Ranoz.gg] No valid links found.")
        return None

    if fake_link: # Otherwise the download cannot be processed
        try:
            session.get(fake_link)
        except:
            pass

    return real_link