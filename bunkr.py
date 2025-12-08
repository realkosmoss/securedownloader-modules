from curl_cffi import requests
from bs4 import BeautifulSoup

from base64 import b64decode
from math import floor
from itertools import cycle

def decrypt(epoch_time, encoded_data_b64):
    key_index = floor(epoch_time / 3600)
    secret = f"SECRET_KEY_{key_index}"

    secret_bytes = secret.encode("utf-8")
    cyclic_key = cycle(secret_bytes)

    encrypted_bytes = b64decode(encoded_data_b64)

    decrypted_data = bytearray(byte ^ next(cyclic_key) for byte in encrypted_bytes)

    return decrypted_data.decode("utf-8", errors="ignore")
    
def bunkr_fetch(session: requests.Session, url: str) -> tuple[str, str] | list[str]:
    """Returns direct download link and filename in a tuple or list."""
    session.headers["referer"] = "https://get.bunkrr.su/"
    url_lower = url.lower()
    if "/a/" in url_lower: # Album
        links = _bunkr_album(session, url)
        return links # Gets automatically handled by the download processing backend
    elif "/file/" in url_lower: # get.bunkrr.su/file/
        return _single_file(session, url)
    else: # Single file link
        filename = _get_filename(session, url)
        dl_link = _bunkr_single(session, url)
        return dl_link, filename

def _get_filename(session, url) -> str:
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    filename = None

    container = soup.find("div", class_="flex-1 grid gap-0.5 auto-rows-max")
    if container:
        h1 = container.find("h1")
        if h1 and h1.get_text(strip=True):
            filename = h1.get_text(strip=True)

    if not filename:
        debug_div = soup.find("div", string=lambda t: t and "Original=" in t)
        if debug_div:
            text = debug_div.get_text(strip=True)
            filename = text.split("Original=")[1].split(",")[0].strip()

    if not filename:
        center_div = soup.find("div", class_="text-center")
        if center_div:
            h1 = center_div.find("h1")
            if h1 and h1.get_text(strip=True):
                filename = h1.get_text(strip=True)

    return filename

def _bunkr_album(session: requests.Session, url: str):
    url_lower = url.lower()
    if "/a/" in url_lower: # Album
        resp = session.get(url)
        if resp.status_code != 200:
            raise Exception("Well, bunkr returned non 200.")
        soup = BeautifulSoup(resp.text, 'html.parser')

        def has_all_classes(tag, tags):
            classes = tag.get('class', [])
            return all(c in classes for c in tags)

        temp_links = [a['href'] for a in soup.find_all('a') if has_all_classes(a, ['after:absolute', 'after:z-10', 'after:inset-0']) and a.has_attr('href')]

        not_direct_links = []
        for link in temp_links:
            not_direct_links.append(f"https://bunkr.cr{link}")
        return not_direct_links

def _bunkr_single(session: requests.Session, url: str) -> str:
    if "/f/" in url.lower():
        resp = session.get(url)
        if resp.status_code != 200:
            raise Exception("Well, bunkr returned non 200 on inner link.")
        soup = BeautifulSoup(resp.text, 'html.parser')
        required_classes = [
            "btn", "btn-main", "btn-lg", "rounded-full", "px-6",
            "font-semibold", "flex-1", "ic-download-01", "ic-before", "before:text-lg"
        ]
        def filter_link_tag(tag):
            if tag.name != 'a' or not tag.has_attr('href') or not tag.has_attr('class'):
                return False
            classes = tag.get('class', [])
            return all(c in classes for c in required_classes)
        link_tag = soup.find(filter_link_tag)
        if link_tag:
            not_direct_link = link_tag['href']
    else:
        not_direct_link = url # guessing its a https://get.bunkrr.su/file/?????
    file_id = not_direct_link.replace("https://get.bunkrr.su/file/", "")
    post_json = {"id": str(file_id)}
    resp = session.post("https://apidl.bunkr.ru/api/_001_v2", json=post_json)
    if not resp.status_code == 200:
        raise Exception("Failed to get required parameters.")
    data = resp.json()
    decrypted = decrypt(data["timestamp"], data["url"])
    return decrypted

def _single_file(session: requests.Session, url: str):
    session.headers["referer"] = "https://get.bunkrr.su/"
    file_id = url.replace("https://get.bunkrr.su/file/", "")
    post_json = {"id": str(file_id)}
    resp = session.post("https://apidl.bunkr.ru/api/_001_v2", json=post_json)
    if not resp.status_code == 200:
        raise Exception("Failed to get required parameters.")
    data = resp.json()
    return decrypt(data["timestamp"], data["url"])