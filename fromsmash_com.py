from curl_cffi import requests
from urllib.parse import quote

api_headers = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://fromsmash.com",
    "priority": "u=1, i",
    "referer": "https://fromsmash.com/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}

def fromsmash_com_fetch(session: requests.Session, url: str):
    cleaned_url = url.replace('https://', '')
    # Prepare
    resp = session.get("https://discovery.fromsmash.co/namespace/public/services?version=02-2023", allow_redirects=True)
    region = resp.json()["region"]
    # Authentication bullshit lmao
    headers = session.headers.copy()
    headers.update(api_headers)
    resp = session.post(f"https://iam.{region}.fromsmash.co/account", json={}, headers=headers)
    token = resp.json()["account"]["token"]["token"]
    headers["Authorization"] = "Bearer " + token
    # Start getting the download link
    resp = session.get(f"https://link.fromsmash.co/target/{quote(cleaned_url, safe='')}?version=10-2019", headers=headers, allow_redirects=True)
    temp_url = resp.json()["target"]["url"]
    # We get the download link now
    headers["smash-authorization"] = ""
    resp = session.get(temp_url + "?version=01-2024", headers=headers) # Dont know why it needs "?version=01-2024" but i mean if it works it works
    DL_LINK = resp.json()["transfer"]["download"]
    return DL_LINK