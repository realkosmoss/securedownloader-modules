from curl_cffi import requests
import time
import urllib.parse, json, hashlib, re

def _solve_captcha(enc: str):
    if not enc:
        raise ValueError("No Set-Cookie header provided")

    m = re.search(r'captcha=("[^"]*"|[^;,\r\n]+)', enc)
    if not m:
        raise ValueError("captcha cookie not found in header")

    token = m.group(1)
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]

    decoded = urllib.parse.unquote_plus(token)

    try:
        data = json.loads(decoded)
    except json.JSONDecodeError as e:
        snippet = decoded[:300].replace("\n","\\n")
        raise ValueError(f"JSON decode failed: {e}. Decoded starts with: {snippet}") from e

    puzzle = data["puzzle"]
    rng = int(data["range"])
    finds = data["find"]

    found = {}
    for n in range(rng):
        s = puzzle + str(n)
        h = hashlib.sha256(s.encode()).hexdigest()
        if h in finds:
            found[finds.index(h)] = n
            if len(found) == len(finds):
                break

    order = [1, 2, 0]
    try:
        nonces = [str(found[i]) for i in order]
    except KeyError:
        raise RuntimeError("Not all nonces were found within range")

    out = " ".join(nonces)
    return out + " " # Replicates what the browser does


def workupload_com_fetch(session: requests.Session, url: str):
    FILE_ID = url.replace("https://", "").replace("http://", "")
    FILE_ID = FILE_ID.replace("workupload.com/file/", "").strip()
    resp = session.get(url, allow_redirects=True)
    if not resp.status_code == 200:
        time.sleep(4)
        resp = session.get(url)
    # Puzzle shit
    api_headers = session.headers.copy()
    api_headers["x-requested-with"] = "XMLHttpRequest"
    puzzle_response = session.get("https://workupload.com/puzzle", headers=api_headers)
    code = _solve_captcha(puzzle_response.headers.get("Set-Cookie"))
    form_data = {"captcha": code}
    puzzle_response = session.post("https://workupload.com/captcha", data=form_data, headers=api_headers)
    # Lets start
    session.get(url) # Needed for new token after solving captcha (Was stuck here debugging everything else not thinking about this for 30 minutes)

    resp = session.get(f"https://workupload.com/api/file/getDownloadServer/{FILE_ID}", headers=api_headers)
    session.headers.update({
        "referer": "https://workupload.com/",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-site",
    })

    return resp.json()["data"]["url"]