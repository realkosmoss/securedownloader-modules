from curl_cffi import requests
from urllib.parse import urlparse
import time

_api_headers = {
   "sec-fetch-dest": "empty",
   "sec-fetch-mode": "cors",
   "sec-fetch-site": "same-origin",
}

def rootz_so_fetch(session: requests.Session, url: str):
    if not "/d/" in url:
        raise Exception("[ROOTZ_SO] Not a valid link.")
    session.get(url)
    _path = urlparse(url).path.strip("/").split("/")
    file_id = _path[1]
    
    api_resp = session.get(f"https://www.rootz.so/api/files/download-by-short/{file_id}")
    if not api_resp.status_code == 200:
        raise Exception("[ROOTZ_SO] Api returned != 200 status_code")
    api_data = api_resp.json()["data"]

    fileId   = api_data.get("fileId")
    fileName = api_data.get("fileName")
    fileUrl  = api_data.get("url") # Legit the download link, its possible to just return this early

    # tracking bullshits because im nice
    tracking_timeout = 5
    _data = {
        "o": url,
        "sv": "0.1.3",
        "sdkn": "@vercel/analytics/next",
        "sdkv": "1.5.0",
        "ts": int(time.time() * 1000),
        "dp": "/d/[shortId]",
        "r": ""
    }
    _temp_headers = {**session.headers, **_api_headers}
    try:
        session.post("https://www.rootz.so/_vercel/insights/view", headers=_temp_headers, json=_data, timeout=tracking_timeout) # OK
        session.get("https://www.rootz.so/api/advertiser/url", headers=_temp_headers, timeout=tracking_timeout)
    except: pass # if these crash then idgaf
    # End of tracking

    resp = session.get(f"https://www.rootz.so/api/files/proxy-download/{fileId}", allow_redirects=False)

    return resp.headers.get("location") or fileUrl, fileName
