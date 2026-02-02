from curl_cffi import requests
from urllib.parse import urlparse

_cors = {
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

def turbo_cr_fetch(session: requests.Session, url: str):
    file_id = urlparse(url).path.rstrip("/").split("/")[-1]

    session.get(url)

    # Captcha? Not even used but okay
    session.get("https://turbo.cr/api/altcha/challenge")
    session.post("https://turbo.cr/api/captcha-verified", headers={**session.headers, **_cors})

    session.cookies.set(name="captcha_verified", value="1", domain="turbo.cr", path="/")
    _resp = session.get(f"https://turbo.cr/api/sign?v={file_id}")
    _data = _resp.json()
    return _data["url"], _data.get("filename") or _data.get("original_filename")