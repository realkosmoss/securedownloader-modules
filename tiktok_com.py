from curl_cffi import requests
import re, json

def _single(resp: requests.Response):
    PlayAddrMatch = re.search(r'"PlayAddr":(\{.*?\})', resp.text, re.DOTALL)
    if PlayAddrMatch:
        PlayAddrStr = PlayAddrMatch.group(1)
    
    DescMatch = re.search(r'"contents":\[\{"desc":"(.*?)"', resp.text, re.DOTALL)
    if DescMatch:
        Desc = DescMatch.group(1)
        Desc = re.sub(r'[<>:"/\\|?*]', '', Desc)[:256].strip()
    else:
        Desc = "Untitled"

    if PlayAddrStr and Desc:
        PlayAddrData = json.loads(PlayAddrStr)
        return PlayAddrData["UrlList"][1], Desc + ".mp4"

def _multi(resp: requests.Response):
    pass

def tiktok_fetch(session: requests.Session, url: str):
    resp = session.get(url)

    if "/video/" in url: # Simple ass scraper
        return _single(resp)
    elif "/@" in url: # Creator (Not gonna support until i find a easier way to scrape all the ids)
        return _multi(resp)
    
    raise Exception("[tiktok] it worked! congrats, you downloaded NOTHING YOU STUPID FUCK")