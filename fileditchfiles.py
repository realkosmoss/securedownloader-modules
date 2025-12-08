# fileditchfiles.me
from curl_cffi import requests
from bs4 import BeautifulSoup
import time

def fileditchfiles_fetch(session: requests.Session, url: str):
    resp = session.get(url) # Can wrap in a try but theres no reason.
    if not resp.status_code == 200: # Rarely happens, im assuming.
        time.sleep(4)
        resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.find("a", class_="download-button")["href"]
    return link