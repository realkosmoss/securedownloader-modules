from curl_cffi import requests
from bs4 import BeautifulSoup

def filemirage_com_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    link_tag = soup.find("a", class_="btn btn-action", attrs={"aria-label": "Download"})
    return link_tag["href"] if link_tag else None