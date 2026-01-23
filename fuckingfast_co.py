from curl_cffi import requests
import re

_cors = {
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

def fuckingfast_co_fetch(session: requests.Session, url: str):
    url = url.split('#')[0] # Saw it on fitgirl-repacks.site
    resp = session.get(url)

    _temp_headers = {**session.headers, **_cors}
    session.post(f"{url}/dl", headers=_temp_headers)

    match = re.search(r'https://fuckingfast\.co/dl/[\w-]+', resp.text)
    download_url = match.group(0) if match else None

    if not download_url:
        raise Exception("[fuckingfast_co] download link not found.")

    return download_url