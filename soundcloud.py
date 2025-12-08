from curl_cffi import requests
from bs4 import BeautifulSoup
import json, re

def _pick_best_stream(transcodings):
    for t in transcodings:
        fmt = t.get("format", {})
        if fmt.get("protocol") == "progressive" and "mpeg" in fmt.get("mime_type", ""):
            return t["url"]

    for t in transcodings:
        fmt = t.get("format", {})
        if fmt.get("protocol") == "hls" and t.get("preset") == "abr_sq":
            return t["url"]

    for t in transcodings:
        if t.get("url"):
            return t["url"]

    return None

def soundcloud_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    scripts_src = soup.find_all("script", src=True)
    for script in scripts_src:
        script_url = script.get("src")
        script_resp = session.get(script_url)
        match = re.search(r'client_id\s*:\s*"([0-9a-zA-Z]+)"', script_resp.text, re.DOTALL)
        if match:
            client_id = match.group(1)
            break

    scripts = soup.find_all("script", src=False)

    if not scripts:
        raise Exception("[soundcloud] Scripts not found.")

    for script in scripts:
        script_text = script.string
        if not script_text:
            continue
        if "window.__sc_hydration" not in script_text:
            continue
        soundData = None
        try:
            json_str = script_text.replace("window.__sc_hydration = ", "").rstrip(";").strip()
            data = json.loads(json_str)

            for item in data:
                if isinstance(item, dict) and item.get("hydratable") == "sound":
                    soundData = item
                    break
        except json.JSONDecodeError:
            pass
        if not soundData:
            raise Exception("[soundcloud] Sound Data Json not found.")
        soundData = soundData["data"]
        track_authorization = soundData["track_authorization"]

        best_url = _pick_best_stream(soundData["media"]["transcodings"])
        client_id = client_id or "0wlyyut4CpbvbdpJVkjVQExyIYX27qGO"
        api_url = f"{best_url}?client_id={client_id}&track_authorization={track_authorization}"
        resp = session.get(api_url)
        track_id = soundData["id"]
        track_title = soundData["title"].replace("/", "_")
        filename = f"{track_id}_{track_title}.mp3"
        return (resp.json()["url"], filename)