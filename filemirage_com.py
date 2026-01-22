from curl_cffi import requests
import re

def filemirage_com_fetch(session: requests.Session, url: str):
    resp = session.get(url)

    pattern = r'window\.location\.href\s*=\s*"([^"]*/file/direct[^"]*)"'

    match = re.search(pattern, resp.text)
    if not match:
        raise Exception("[filemirage] Couldnt find the direct link")
    _url = match.group(1)

    _resp = session.get(_url, allow_redirects=False)
    _direct_link = _resp.headers.get("location")

    return _direct_link
