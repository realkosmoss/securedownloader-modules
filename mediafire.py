from curl_cffi import requests
from bs4 import BeautifulSoup
import base64
import re

def mediafire_fetch(session: requests.Session, url: str) -> str | None:
    if not "/folder/" in url.lower(): # if its not a folder
        url_fix = url.replace("http://", "https://")
        resp = session.get(url_fix) # fixes some rare issues if you enter a http url
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        dl_button = soup.select_one('a#downloadButton')

        if not dl_button:
            return None

        scrambled = dl_button.get('data-scrambled-url')
        if scrambled:
            try:
                return base64.urlsafe_b64decode(scrambled).decode()
            except Exception:
                return None

        href = dl_button.get('href')
        if href:
            return href

        return None
    else: # Gr8 handling mate
        match = re.search(r"/folder/([^/]+)", url)
        download_links = []
        if match:
            folder_id = match.group(1)
            resp = session.get(f"https://www.mediafire.com/api/1.4/folder/get_content.php?r=jbla&content_type=files&filter=all&order_by=name&order_direction=asc&chunk=1&version=1.5&folder_key={folder_id}&response_format=json")
            data = resp.json()
            files = data["response"]["folder_content"]["files"]
            for file in files:
                download_links.append(file["links"]["normal_download"])
        return download_links