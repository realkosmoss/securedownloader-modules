from curl_cffi import requests
from bs4 import BeautifulSoup
import json, re

def _fetch_reel(session: requests.Session, url: str):
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    script_tags = soup.find_all("script", {"type": "application/json"})
    
    for script in script_tags:
        if not script.string:
            continue
        if "video_versions" in script.string or "RelayPrefetchedStreamCache" in script.string:
            data = json.loads(script.string)
            results = []
            stack = [data]
            
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    for key, value in current.items():
                        if key == "video_versions":
                            results.append(value)
                        else:
                            stack.append(value)
                elif isinstance(current, list):
                    for item in current:
                        stack.append(item)

            if not results:
                continue

            all_videos = [video for sublist in results for video in sublist]
            best_video = max(all_videos, key=lambda v: v.get("width", 0))
            
            caption_text = None
            stack = [data]
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    for key, value in current.items():
                        if key == "caption" and isinstance(value, dict) and "text" in value:
                            caption_text = value["text"]
                            break
                        else:
                            stack.append(value)
                elif isinstance(current, list):
                    for item in current:
                        stack.append(item)
            if not caption_text and not best_video:
                continue
            safe_caption = re.sub(r"#\w+", "", caption_text)
            safe_caption = re.sub(r'[<>:"/\\|?*]', "_", safe_caption)
            safe_caption = re.sub(r"\s+", " ", safe_caption).strip()
            safe_caption = safe_caption[:100] or "video"
            return best_video["url"], f"{safe_caption}.mp4"

def _find_all_media(obj):
    found = []
    if isinstance(obj, dict):
        if "xig_polaris_media" in obj:
            found.append(obj["xig_polaris_media"])
        for v in obj.values():
            found.extend(_find_all_media(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_all_media(item))
    return found

def _find_key(obj, target_key):
    if isinstance(obj, dict):
        if target_key in obj:
            return obj[target_key]
        for v in obj.values():
            result = _find_key(v, target_key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_key(item, target_key)
            if result is not None:
                return result
    return None

def _get(session: requests.Session, url: str, key: str):
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    for script in soup.find_all("script", {"type": "application/json"}):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        timeline_items = _find_key(data, key)
        if timeline_items:
            return timeline_items.get("items", [])

    return []


def _fetch_post(session: requests.Session, url: str):
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    FOUND_MEDIA_LINKS = []

    scripts = soup.find_all('script', type='application/json')
    for script in scripts:
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        media_list = _find_all_media(data)
        for media in media_list:
            if not media:
                continue
            if_not_gated_logged_out = media.get("if_not_gated_logged_out", {})
            
            carousel = if_not_gated_logged_out.get("carousel_media") or []
            for item in carousel:
                img_candidates = item.get("image_versions2", {}).get("candidates", [])
                if img_candidates:
                    FOUND_MEDIA_LINKS.append(img_candidates[0]["url"])
                
                vid_candidates = item.get("video_versions", [])
                if vid_candidates:
                    FOUND_MEDIA_LINKS.append(vid_candidates[0]["url"])
            
            video_versions = if_not_gated_logged_out.get("video_versions", [])
            if video_versions:
                highest_video = max(video_versions, key=lambda x: x.get("type", 0))
                FOUND_MEDIA_LINKS.append(highest_video.get("url"))

    # Method 2
    match = re.search(r"/p/([^/?]+)", url)
    real_post_id = match.group(1) if match else None

    #media_list = _get(session, url, "xdt_api__v1__profile_timeline") # Fuck off with this fuck sake dude. (This only finds .pngs.. no videos)
    media_list = _get(session, url, "xdt_api__v1__media__shortcode__web_info")

    for temp_media in media_list:
        temp_post_id = temp_media.get("shortcode") or temp_media.get("code") or "unknown"
        if temp_post_id == real_post_id:
            _carousel_media = temp_media.get("carousel_media", []) or []

            for _media in _carousel_media:
                img_candidates = _media.get("image_versions2", {}).get("candidates") or []
                if img_candidates:
                    FOUND_MEDIA_LINKS.append(img_candidates[0]["url"])

                vid_candidates = _media.get("video_versions") or []
                if vid_candidates:
                    FOUND_MEDIA_LINKS.append(vid_candidates[0]["url"])
            break

    return list(dict.fromkeys(FOUND_MEDIA_LINKS))

def instagram_com_fetch(session: requests.Session, url: str):
    if "/reel/" in url:
        return _fetch_reel(session, url)
    elif "/p/" in url:
        return _fetch_post(session, url)
    return None