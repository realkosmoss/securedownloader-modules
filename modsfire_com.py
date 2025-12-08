from curl_cffi import requests
from bs4 import BeautifulSoup

BASE_URL = "https://modsfire.com"

def modsfire_com_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    fileId = url.replace("https://modsfire.com/", "")

    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.find("a", class_="download-button")
    if link:
        href = link.get("href")
    session.get(BASE_URL + href) # For cookies only
    resp = session.get("https://modsfire.com/d/" + fileId, allow_redirects=False)
    session.headers["referer"] = "https://modsfire.com/"
    return resp.redirect_url