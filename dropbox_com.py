from curl_cffi import requests

def dropbox_com_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    csrf = resp.cookies.get("__Host-js_csrf")
    
    session.headers["origin"] = "https://www.dropbox.com"
    session.headers["x-csrf-token"] = csrf
    session.headers["x-dropbox-client-yaps-attribution"] = "edison_atlasservlet.file_viewer-edison:prod"
    session.headers["x-dropbox-uid"] = "-1"

    data = {
        "link_url": url,
        "optional_grant_book": "",
        "optional_rlkey": ""
    }
    session.headers["referer"] = url
    resp = session.post("https://www.dropbox.com/2/sharing_receiving/generate_download_url", json=data)
    return resp.json()["download_url"]