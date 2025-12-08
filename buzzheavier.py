from curl_cffi import requests

def buzzheavier_fetch(session: requests.Session, url: str) -> str | None:
    if not "/download" in url:
        url = url.rstrip("/") + "/download"
    
    headers = session.headers.copy()
    headers.update({
        "hx-current-url": url.replace("/download", ""),
        "hx-request": "true",
        "referer": url.replace("/download", ""),
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    })

    resp = session.get(url, headers=headers)
    return resp.headers.get("hx-redirect")