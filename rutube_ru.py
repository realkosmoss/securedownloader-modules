from curl_cffi import requests

def rutube_ru_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    if not resp.status_code == 200:
        raise Exception("[RuTube] Failed Session.get line 6, ", url)
    video_id = url.replace("http://", "").replace("https://", "").replace("rutube.ru/video/", "").split("/")[0]
    api_url = f"https://rutube.ru/api/play/options/{video_id}/?no_404=true&referer=https%253A%252F%252Frutube.ru&pver=v2&client=wdp&2k=1&av1=1"
    resp = session.get(api_url)
    if not resp.status_code == 200:
        raise Exception("[RuTube] Failed to get api url, line 11")
    data = resp.json()
    video_name = data.get("title")
    video_balancer = data.get("video_balancer") or {}
    DL_LINK_HLS = video_balancer.get("m3u8", "")
    DL_LINK = video_balancer.get("default", "")
    if DL_LINK_HLS:
        return DL_LINK_HLS, video_name
    elif DL_LINK:
        return DL_LINK, video_name
    else:

        raise Exception("[RuTube] No download link found.")
