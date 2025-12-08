# Tried my best but couldnt figure it out
# Thanks! https://github.com/mikf/gallery-dl/blob/master/gallery_dl/extractor/chevereto.py#L60
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import binascii

def decrypt_xor(encrypted, key, base64=True, fromhex=False):
    if base64:
        encrypted = binascii.a2b_base64(encrypted)
    if fromhex:
        encrypted = bytes.fromhex(encrypted.decode())

    div = len(key)
    return bytes([
        encrypted[i] ^ key[i % div]
        for i in range(len(encrypted))
    ]).decode()

def jpg_su_fetch(session: requests.Session, page_url: str):
    resp = session.get(page_url)
    page = resp.text
    m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    if m:
        url = m.group(1)
    else:
        url = None
        pos = page.find(" download=")
        if pos != -1:
            start = max(0, pos - 500)
            end = pos + 500
            m2 = re.search(r'href="([^"]+)"', page[start:end])
            if m2:
                url = m2.group(1)
        if not url:
            soup = BeautifulSoup(page, "html.parser")
            btn = soup.select_one("a.btn.btn-download.default")
            if btn and btn.has_attr("href"):
                url = btn["href"]
            else:
                img = soup.select_one("img.lazy[data-src]")
                if img and img.has_attr("data-src"):
                    url = img["data-src"]
    if not url:
        raise RuntimeError("getting the direct link failed, are you sure you entered a correct url?")
    if not url.startswith("https://"):
        key = b"seltilovessimpcity@simpcityhatesscrapers"
        url = decrypt_xor(url, key, fromhex=True)
    return url