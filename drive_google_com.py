from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import re

def _pick_best(streams):
    best = None
    for s in streams:
        meta = s.get("transcodeMetadata", {})
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        bitrate = meta.get("maxContainerBitrate", 0)

        if best is None:
            best = s
            continue

        best_meta = best.get("transcodeMetadata", {})
        best_width = best_meta.get("width", 0)
        best_height = best_meta.get("height", 0)
        best_bitrate = best_meta.get("maxContainerBitrate", 0)

        if (width * height) > (best_width * best_height):
            best = s
        elif (width * height) == (best_width * best_height) and bitrate > best_bitrate:
            best = s

    return best["url"] if best else None

def drive_google_com_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    
    # Used for backup method
    m = re.search(r'/d/([A-Za-z0-9_-]+)/view(?:\?.*)?', url)
    file_id = m.group(1) if m else None

    filename = file_id or "drive_download"

    filenameMatch = re.search(r"<title>(.*?) - Google Drive</title>", resp.text)
    if filenameMatch:
        filename = filenameMatch.group(1)
        
    KEY = None
    configJsonMatch = re.search(r"configJson:\s*(\[[\s\S]*?\])", resp.text)
    if configJsonMatch:
        configJsonStr = configJsonMatch.group(1)
        configJsonStr = configJsonStr.replace("undefined", "null")
        configJsonStr = re.sub(r",\s*(\]|\})", r"\1", configJsonStr)
        keyMatch = re.search(r'https://clients\d+\.google\.com",null,"(AIza[0-9A-Za-z\-_]{35})"', configJsonStr)
        if keyMatch:
            KEY = keyMatch.group(1)
    # <----> (End of backup)

    itemJsonMatch = re.search(r"itemJson:\s*(\[[\s\S]*?\])\s*}", resp.text)
    if not itemJsonMatch:
        raise ValueError("itemJson not found. ??? Deleted, privated?")
    
    itemJsonStr = itemJsonMatch.group(1)
    itemJsonStr = itemJsonStr.replace("undefined", "null")
    itemJsonStr = re.sub(r",\s*(\]|\})", r"\1", itemJsonStr)

    itemJson = json.loads(itemJsonStr)
    downloadUrl, resource_key = None, None
    for bs in itemJson:
        if not bs:
            continue
        if "&export=download" in str(bs):
            downloadUrl = bs
        if isinstance(bs, list):
            for sub in bs:
                if isinstance(sub, list) and len(sub) > 1:
                    _, resource_key = sub[:2]
        if downloadUrl and resource_key: # yes if only downloadUrl is found then it will loop through the full one anyways then break, still faster than 2 loops
            break
    if not downloadUrl: # We try extracting the VIDEO url if its a video (This is the backup)
        if not KEY:
            raise Exception("[Drive.google.com] Failed, both normal and backup. (No configJson or Key)")
        downloadUrl = f"https://content-workspacevideo-pa.googleapis.com/v1/drive/media/{file_id}/playback?key={KEY}&%24unique=gc999"
        session.headers["referer"] = "https://drive.google.com/"
        resp = session.get(downloadUrl)
        data = resp.json()
        if "error" in data:
            err = data["error"]
            code = err.get("code")
            message = err.get("message", "Unknown Drive error")
            if code == 429:
                raise Exception("[Drive] The limit has been hit for viewers who aren't signed in.")
            raise Exception(f"[Drive] API error {code}: {message}")
        streams = data["mediaStreamingData"]["formatStreamingData"]["progressiveTranscodes"]
        best_url = _pick_best(streams)
        return best_url, filename + ("" if filename.endswith(".mp4") else ".mp4")
    resp2 = session.get(downloadUrl)
    soup = BeautifulSoup(resp2.text, 'html.parser')

    form = soup.find('form', {'id': 'download-form'})
    if not form:
        raise ValueError("Download form not found")

    action_url = form.get('action')
    inputs = form.find_all('input', {'type': 'hidden'})
    params = {inp['name']: inp['value'] for inp in inputs if inp.has_attr('name') and inp.has_attr('value')}
    if resource_key:
        DL_LINK = f'{action_url}?id={params["id"]}&export={params["export"]}&resourcekey={resource_key}&confirm={params["confirm"]}&uuid={params["uuid"]}'
    else:
        DL_LINK = f'{action_url}?id={params["id"]}&export={params["export"]}&confirm={params["confirm"]}&uuid={params["uuid"]}'
    return DL_LINK
