import re
import requests
from bs4 import BeautifulSoup

def uqload_cx_fetch(session: requests.Session, url: str):
    session.get("https://uqload.cx/")
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    scripts = soup.find_all("script")

    video_url = None
    title = None

    for script in scripts:
        if script.string and "new Clappr.Player" in script.string:
            js = script.string

            match_source = re.search(r'sources:\s*\[(.*?)\]', js, re.S)
            if match_source:
                url_match = re.search(r'"(https?://[^"]+)"', match_source.group(1))
                if url_match:
                    video_url = url_match.group(1)

            match_title = re.search(r'title:\s*"([^"]+)"', js)
            if match_title:
                title = match_title.group(1)

            break
    session.headers.update({
        "Accept": "*/*",
        "Accept-Encoding": "identity;q=1, *;q=0",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Range": "bytes=0-",
        "Referer": "https://uqload.cx/",
        "Sec-Fetch-Dest": "video",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
    })
    return video_url, f"{title}.mp4"
