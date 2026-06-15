from curl_cffi import requests
from urllib.parse import urlparse
import json, time, hashlib, math

_api_cors = {
    "origin": "https://gofile.io",
    "referer": "https://gofile.io/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
}

def generateWT(token: str, user_agent: str, language: str) -> str:
    now_seconds = time.time()
    time_chunk = math.floor(now_seconds / 14400)
    
    raw_string = f"{user_agent}::{language}::{token}::{time_chunk}::9844d94d963d30"
    
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

def gofile_io_fetch(session: requests.Session, url: str):
    session.get(url)
    fileId = urlparse(url).path.strip("/").split("/")[-1]

    _temp_api_headers = {**session.headers, **_api_cors}
    # Get account
    api_resp = session.post("https://api.gofile.io/accounts", headers=_temp_api_headers)
    if "error-rateLimit" in api_resp.text:
        raise Exception("[GOFILE] Ratelimited")
    elif not "rootFolder" in api_resp.text:
        raise Exception("[GOFILE] content api returned some weird shit")
    api_data = api_resp.json()
    account_token = api_data.get("data").get("token")
    # Set the cookie for downloading with this session later, if you do that in your backend that is
    session.cookies.set(
        "accountToken",
        account_token,
        domain=".gofile.io",
        path="/"
    )

    session.get(
        "https://api.gofile.io/accounts/website",
        headers={
            **_temp_api_headers,
            "authorization": f"Bearer {account_token}",
        }
    )

    # tracking lalala
    _temp_tracking_data = {"n": "pageview",
                           "u": url,
                           "d": "gofile.io",
                           "r": None}
    _temp_tracking_headers = {
        **session.headers,
        **_api_cors,
        "Content-Type": "text/plain",
    }
    try:
        session.post("https://s.gofile.io/api/event", headers=_temp_tracking_headers, data=json.dumps(_temp_tracking_data))
    except: pass

    # fetch shit now
    ua = session.headers.get("user-agent")
    accept_lang = session.headers.get("accept-language", "")
    lang = accept_lang.split(",")[0].split(";")[0] or "en-US"

    wt = generateWT(account_token, ua, lang)

    _temp_api_headers.update({
        "authorization": f"Bearer {account_token}",
        "x-website-token": wt,
        "x-bl": lang
    })
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
        link = child.get("link")
        if link: # folders have no link
            _links.append(link)
    return _links
