# <2025-12-18>
from curl_cffi import requests
from urllib.parse import urlparse
import re, json

_api_cors = {
        "origin": "https://gofile.io",
        "referer": "https://gofile.io/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site"
    }

def gofile_io_fetch(session: requests.Session, url: str):
    session.get(url)
    fileId = urlparse(url).path.strip("/").split("/")[-1]

    # Get Appdata WT
    resp = session.get("https://gofile.io/dist/js/config.js")
    _AppdataMatch = re.search(r'appdata\.wt\s*=\s*([\'"])(.*?)\1', resp.text)
    if not _AppdataMatch:
        raise Exception("[GOFILE] Appdata WT not found")
    AppdataWT = _AppdataMatch.group(2)

    _temp_api_headers = {**session.headers, **_api_cors}
    # Get account
    api_resp = session.post("https://api.gofile.io/accounts", headers=_temp_api_headers)
    if "error-rateLimit" in api_resp.text:
        raise Exception("[GOFILE] Ratelimited")
    elif not "rootFolder" in api_resp.text:
        raise Exception("[GOFILE] content api returned some weird shit")
    api_data = api_resp.json()
    account_token = api_data.get("data").get("token")

    # tracking lalala
    _temp_data = {
        "n": "pageview",
        "u": url,
        "d": "gofile.io",
        "r": None
    }
    _temp_tracking_headers = {
        **session.headers,
        **_api_cors,
        "Content-Type": "text/plain",
    }
    try:
        session.post("https://s.gofile.io/api/event", headers=_temp_tracking_headers, data=json.dumps(_temp_data))
    except: pass

    # downloading shit now
    _temp_api_headers.update({"authorization": f"Bearer {account_token}", "x-website-token": AppdataWT})
    resp = session.get(f"https://api.gofile.io/contents/{fileId}?contentFilter=&page=1&pageSize=1000&sortField=name&sortDirection=1", headers=_temp_api_headers)
    _data = resp.json()
    _status = _data.get("status")
    if not _status == "ok":
        raise Exception("[GOFILE] Content api returned status", _status)
    _links = []
    data = _data.get("data")
    _children = data.get("children", {})
    for child in _children.values():
        if not child.get("canAccess"):
            continue
        _links.append(child.get("link"))
    return _links
