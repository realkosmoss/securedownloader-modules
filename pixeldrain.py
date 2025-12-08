from curl_cffi import requests
import json, re

# OLD pixeldrain code saved for meming purposes
#def pixeldrain_fetch(session: requests.Session, url: str) -> list[str]:
#    url_lower = url.lower()
#    if "pixeldrain.com/l/" in url_lower: # album
#        resp = session.get(url)
#        data = None
#        for line in resp.text.splitlines():
#            if line.strip().startswith("window.viewer_data ="):
#                data_str = line.strip().replace("window.viewer_data =", "").rstrip(";").strip()
#                data = json.loads(data_str)
#                break
#
#        if data and data["type"].lower() == "list":
#            files = data.get("api_response", {}).get("files", [])
#            fileIds = []
#            directLinks = []
#            for file in files:
#                fileId = file["detail_href"].replace("/file/", "").replace("/info", "")
#                fileIds.append(fileId)
#            for fileId in fileIds:
#                resp = session.get(f"https://pixeldrain.com/u/{fileId}")
#                # Handle videos (Commented it out as it MIGHT download an lower quality version.)
#                #soup = BeautifulSoup(resp.text, 'html.parser')
#                #meta_tag = soup.find('meta', property='og:video')
#                #if meta_tag:
#                #    download_url = meta_tag.get("content")
#                #    if download_url:
#                #        directLinks.append(download_url)
#                #        continue
#                # if not a video then well.. fuck.. (Suprisingly easy.)
#                directLinks.append(f"https://pixeldrain.com/api/file/{fileId}?download")
#                continue
#            return directLinks
#    elif "pixeldrain.com/u/" in url_lower: # Single file
#        fileId = url.replace("pixeldrain.com/u/", "").replace("http://", "").replace("https://", "").replace("/", "").strip()
#        return f"https://pixeldrain.com/api/file/{fileId}?download"

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