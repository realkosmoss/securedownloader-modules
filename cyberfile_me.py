from curl_cffi import requests
import re

def cyberfile_me_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    file_id = None
    match = re.search(r'showFileInformation\((\d+)\);', resp.text)
    if match:
        file_id = match.group(1)
    if not file_id:
        raise Exception("[Cyberfile.me] FileId not found.")
    resp = session.post("https://cyberfile.me/account/ajax/file_details", data={"u": str(file_id)})
    shit_html = resp.json()["html"]
    match = re.search(r'onClick="openUrl\(\'([^\']+)\'\);', shit_html)
    if match:
        url = match.group(1)
        return url