from curl_cffi import requests
import json, re

api_cors = {
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site"
    }
standard_cors = {
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none"
    }

def pixeldrain_fetch(session: requests.Session, url: str):
    resp = session.get(url)
    session.headers.update(api_cors)
    event = {
        "n": "pageview",
        "u": url,
        "d": "pixeldrain.com", # pixeldrain.com or not doesnt matter, its the same ip anyways (on both pixeldrain.com and pixeldrain.dev)
        "r": None,
    }
    session.post("https://stats.pixeldrain.com/api/event", json=event)
    session.headers.update(standard_cors)
    ul = url.lower()
    if "/l/" in ul:
        api_data_pattern = r"window\.viewer_data\s*=\s*(\{.*?\});"
        api_data_match = re.search(api_data_pattern, resp.text, flags=re.DOTALL)
        if not api_data_match:
            raise Exception("[pixeldrain] No api data json match.")
        api_data = json.loads(api_data_match.group(1).replace("window.viewer_data = ", "").strip())

        files_to_return = []
        for file in api_data.get("api_response").get("files"):
            files_to_return.append(f"https://pixeldrain.com/u/{file['id']}")
        return files_to_return
    elif "/u/" in ul:
        file_id = url.replace("http://", "https://").replace(".dev", ".com").replace("https://pixeldrain.com/u/", "").split("/")[0]
        return f"https://pixeldrain.com/api/file/{file_id}?download"

    raise Exception("[pixeldrain] Everything failed? What the fuck did you pass into me?")
