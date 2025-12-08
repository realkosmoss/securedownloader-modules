from curl_cffi import requests
from urllib.parse import urlparse
import math

def kemono_cr_fetch(session: requests.Session, url: str):
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")

    service = parts[0]
    user_index = parts.index("user") + 1
    whore_id = parts[user_index]
    session.headers["accept"] = "text/css"
    download_links = []
    if not "/post/" in url: # Download whole profile
        resp = session.get(f"https://kemono.cr/api/v1/{service}/user/{whore_id}/profile")
        data = resp.json()
        per_page = 50
        page = 0
        max_page = math.ceil(data["post_count"] / per_page)

        for page in range(max_page):
            offset = page * per_page
            resp = session.get(f"https://kemono.cr/api/v1/{service}/user/{whore_id}/posts?o={offset}")
            posts = resp.json()
            for post in posts:
                attachments = post.get("attachments", [])
                for attachment in attachments:
                    download_links.append(f"https://kemono.cr{attachment['path']}?f={attachment['name']}")
        return download_links
    else:
        post_index = parts.index("post") + 1
        post_id = parts[post_index]

        resp = session.get(f"https://kemono.cr/api/v1/{service}/user/{whore_id}/post/{post_id}")
        data = resp.json()
        post = data["post"]
        attachments = post.get("attachments", [])
        for attachment in attachments:
            download_links.append(f"https://kemono.cr{attachment['path']}?f={attachment['name']}")
        attachments = data.get("attachments", [])
        for attachment in attachments:
            download_links.append(f"{attachment['server']}/data/{attachment['path']}?f={post['title']}{attachment['extension']}")
        return download_links