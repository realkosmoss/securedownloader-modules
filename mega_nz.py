from curl_cffi import requests
import base64, json, os, time
from Crypto.Cipher import AES
import threading
from queue import Queue

# Unrelated to mega but its the download printing logic
def _human_bytes(n):
    if n is None:
        return "?? B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    n = float(n)
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f"{n:,.2f} {units[i]}"

def _human_time(seconds):
    if seconds is None:
        return "--:--:--"
    try:
        seconds = int(seconds)
    except Exception:
        return "--:--:--"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# Small helper for api bullshits lol
api_cors = {
        "content-type": "text/plain;charset=UTF-8",
        "origin": "https://mega.nz",
        "referer": "https://mega.nz/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site"
    }
def _api_post(session: requests.Session, url: str, *args, **kwargs):
    headers = {**session.headers, **api_cors}
    return session.post(url, *args, headers=headers, **kwargs)

# Decryption helpers
def extract_url_keys(url: str):
    base, key = url.split('#', 1)
    file_id = base.rstrip('/').split('/')[-1]
    key = key.replace('-', '+').replace('_', '/')
    key += '=' * (-len(key) % 4)
    return file_id, key

def derive_keys(b64_key):
    key_bytes = base64.b64decode(b64_key)
    if len(key_bytes) != 32:
        raise ValueError("[MEGA] key is wrong dude, the len is not 32")

    k = [int.from_bytes(key_bytes[i*4:(i+1)*4], "big") for i in range(8)]
    # AES key = [k0 ^ k4, k1 ^ k5, k2 ^ k6, k3 ^ k7]
    aes_words = [k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7]]
    aes_key = b''.join(w.to_bytes(4, "big") for w in aes_words)
    # IV = [k4, k5, 0, 0]
    iv = (k[4].to_bytes(4, "big") + 
          k[5].to_bytes(4, "big") + 
          b'\x00'*8)
    return aes_key, iv

def _bytes_to_a32(b: bytes):
    if len(b) % 4:
        b += b'\0' * (4 - len(b) % 4)
    return [int.from_bytes(b[i:i+4], "big") for i in range(0, len(b), 4)]

def _b64_url_decode(s: str):
    s = s.replace('-', '+').replace('_', '/')
    s += '=' * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s)

def _a32_to_bytes(a: list[int]):
    return b"".join((x & 0xFFFFFFFF).to_bytes(4, "big") for x in a)

def _base64_to_a32(s: str):
    return _bytes_to_a32(_b64_url_decode(s))

def _decrypt_node_key(enc_key_b64: str, shared_key_a32: list[int]):
    encrypted_a32 = _base64_to_a32(enc_key_b64)
    key_bytes = _a32_to_bytes(shared_key_a32)
    cipher = AES.new(key_bytes, AES.MODE_ECB)

    out: list[int] = []
    for i in range(0, len(encrypted_a32), 4):
        block = _a32_to_bytes(encrypted_a32[i:i+4])
        dec = cipher.decrypt(block)
        out.extend(_bytes_to_a32(dec))
    return out

def decrypt_attributes(enc_attrs, aes_key):
    enc = enc_attrs.replace('-', '+').replace('_', '/')
    enc += '=' * (-len(enc) % 4)
    data = base64.b64decode(enc)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv=b'\x00' * 16)
    decrypted = cipher.decrypt(data)
    try:
        json_str = decrypted.decode("utf-8").strip("\x00")
    except UnicodeDecodeError:
        raise ValueError("[MEGA] bad key or fucked attributes")
    if not json_str.startswith("MEGA"):
        raise ValueError("[MEGA] uhh attributes header is fucked?")
    return json.loads(json_str[4:])

def decrypt_chunk(chunk_enc, aes_key, iv, task_offset):
    counter_int = int.from_bytes(iv, 'big') + (task_offset // 16)
    cipher = AES.new(aes_key, AES.MODE_CTR, initial_value=counter_int, nonce=b'')
    return cipher.decrypt(chunk_enc)

# mega regions
api_hosts = ['g', 'eu', 'us', 'asia']

def _mega_nz_folder(session: requests.Session, url: str):
    folder_id, folder_key_b64 = extract_url_keys(url)

    folder_key_raw = base64.b64decode(folder_key_b64)
    shared_key_a32 = _bytes_to_a32(folder_key_raw)

    api_data = [{"a": "f", "c": 1, "r": 1, "ca": 1}]
    rid = int.from_bytes(os.urandom(4), "big")
    for host in api_hosts:
        try:
            resp = _api_post(
                session,
                f"https://{host}.api.mega.co.nz/cs?id={rid}&n={folder_id}",
                json=api_data,
            )
        except:
            pass
        if resp.status_code == 200:
            break
    folder_contents = resp.json()[0]["f"]

    for node in folder_contents:
        if node.get("t") != 0:
            continue

        file_id = node["h"]
        enc_key_b64 = node["k"].split(":")[1]

        key_words = _decrypt_node_key(enc_key_b64, shared_key_a32)
        if len(key_words) < 8:
            print(f"[MEGA] skip {file_id} (weird key len {len(key_words)})")
            continue

        # grrrrr
        file_key_words = [
            key_words[0] ^ key_words[4],
            key_words[1] ^ key_words[5],
            key_words[2] ^ key_words[6],
            key_words[3] ^ key_words[7],
        ]
        file_iv_words = [key_words[4], key_words[5], 0, 0]

        file_key_aes = _a32_to_bytes(file_key_words)
        file_iv = _a32_to_bytes(file_iv_words)

        rid2 = int.from_bytes(os.urandom(4), "big")
        dl_req = [{"a": "g", "g": 1, "n": file_id}]
        for host in api_hosts:
            try:
                dl_resp = _api_post(
                    session,
                    f"https://{host}.api.mega.co.nz/cs?id={rid2}&n={folder_id}",
                    json=dl_req,
                )
            except:
                pass
            if dl_resp.status_code == 200:
                break
        dl_node = dl_resp.json()[0]

        if not isinstance(dl_node, dict) or "g" not in dl_node:
            print(f"[MEGA] cant download {file_id} (API said {dl_node})")
            continue

        attrs = decrypt_attributes(dl_node["at"], file_key_aes)
        filename = attrs["n"]
        size = dl_node["s"]
        dl_url = dl_node["g"]
        
        _download(session, dl_url, size, filename, file_key_aes, file_iv)
        
def _mega_nz_single(session: requests.Session, url: str):
    file_id, file_key = extract_url_keys(url)
    file_key_aes, file_key_iv = derive_keys(file_key)

    api_data = [{
        "a": "g",
        "g": 1, # request download link, even tho frontend is doing "ad" g returns file download shit, probably looked at the wrong request tho
        "p": file_id
    }]
    for host in api_hosts:
        try:
            resp = _api_post(session, f"https://{host}.api.mega.co.nz/cs?id=0&v=2", json=api_data)
        except:
            pass
        if resp.status_code == 200:
            break
    node = resp.json()[0]
    attrs = decrypt_attributes(node["at"], file_key_aes)
    filename = attrs["n"]
    size = node["s"]
    dl_url = node["g"]
    _download(session, dl_url, size, filename, file_key_aes, file_key_iv)

def _download(our_session, dl_url, size, filename, file_key_aes, file_key_iv):
    # prepare for download
    initial_chunk = 128 * 1024
    max_chunk = 120 * 1024 * 1024
    curr_chunk = initial_chunk

    save_prefix = 0
    save_path = os.path.join(os.getcwd(), filename)
    offset = 0

    while True: 
        # Checks if the file is already there, 
        # if is and its not the size of the mega file, 
        # it will start downloading the needed chunks to complete it, 
        # and checks if its already downloaded and adds prefix so it doesnt replace anything
        if os.path.exists(save_path):
            tmp_offset = os.path.getsize(save_path)

            if tmp_offset < size:
                # its smaller than the mega size so it guesses its the incomplete file and downloads the chunks
                offset = tmp_offset
                break
            else:
                base, ext = os.path.splitext(filename)
                save_path = os.path.join(os.getcwd(), f"{base}({save_prefix}){ext}")
                save_prefix += 1
        else:
            open(save_path, "wb").close()
            offset = 0
            break

    # prepare threading
    q = Queue()
    file_lock = threading.Lock()
    progress_lock = threading.Lock()

    bytes_downloaded = offset
    start = time.time()
    last_line_len = 0
    THREADS = 12#9

    # Shitty fucking printer thread because the printing logic inside of the downloading worker slowed speeds horrendously
    stopthefuckingprintthread = threading.Event()
    def progress_thread():
        nonlocal last_line_len
        while not stopthefuckingprintthread.is_set():
            with progress_lock:
                bd = bytes_downloaded

            elapsed = max(time.time() - start, 1e-6)
            speed_bps = bd / elapsed
            speed_mbps = (speed_bps * 8) / (1024*1024)
            percent = bd / size * 100
            remaining = max(size - bd, 0)
            eta = remaining / speed_bps if speed_bps > 0 else None

            line = (f"Downloaded {_human_bytes(bd)} / {_human_bytes(size)} "
                    f"({percent:5.1f}%) — {speed_mbps:5.2f} Mbps — ETA {_human_time(eta)}")
            pad = " " * max(0, last_line_len - len(line))
            print("\r" + line + pad, end="", flush=True)
            last_line_len = len(line)

            if bd >= size: # Stop if download is complete yes very nice
                stopthefuckingprintthread.set()
                break
            time.sleep(0.1)
    threading.Thread(target=progress_thread, daemon=True).start() # start it yes

    our_session_proxies = our_session.proxies

    def worker():
        nonlocal bytes_downloaded, last_line_len
        dl_session = requests.Session()  # Mega doesnt allow fingerprinted requests for downloads
        dl_session.proxies = our_session_proxies

        while True:
            item = q.get()
            if item is None:
                return

            task_offset, task_size = item
            end = task_offset + task_size - 1

            headers = {'Range': f'bytes={task_offset}-{end}'}
            resp = dl_session.get(dl_url, headers=headers)
            resp.raise_for_status()
            chunk_enc = resp.content

            chunk = decrypt_chunk(chunk_enc, file_key_aes, file_key_iv, task_offset)

            with file_lock:
                with open(save_path, "r+b") as f:
                    f.seek(task_offset)
                    f.write(chunk)
                    f.flush()

            with progress_lock:
                bytes_downloaded += len(chunk)

                elapsed = time.time() - start
                elapsed = max(elapsed, 1e-6)
                speed_bps = bytes_downloaded / elapsed
                speed_mbps = (speed_bps * 8) / (1024 * 1024)

                percent = bytes_downloaded / size * 100
                remaining = max(size - bytes_downloaded, 0)
                eta = remaining / speed_bps if speed_bps > 0 else None
                total_str = _human_bytes(size)

                line = (f"Downloaded {_human_bytes(bytes_downloaded)} / {total_str} ({percent:5.1f}%) — {speed_mbps:5.2f} Mbps — ETA {_human_time(eta)}")
                pad = " " * max(0, last_line_len - len(line))
                print("\r" + line + pad, end="", flush=True)
                last_line_len = len(line)

            q.task_done()

    threads = []
    for _ in range(THREADS):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    current = offset
    while current < size:
        chunk_size = min(curr_chunk, size - current)
        q.put((current, chunk_size))
        current += chunk_size
        if curr_chunk < max_chunk:
            curr_chunk = min(curr_chunk + initial_chunk, max_chunk)

    q.join()
    for _ in threads:
        q.put(None)
    stopthefuckingprintthread.set() # stops printing thread

    end = time.time()
    total_bytes = os.path.getsize(save_path)
    elapsed = max(end - start, 1e-6)
    speed_mbps = (total_bytes * 8) / (elapsed * 1024 * 1024)

    final = (f"Downloaded {_human_bytes(total_bytes)} in {_human_time(elapsed)} "
             f"({speed_mbps:.2f} Mbps) -> {save_path}")
    print("\r" + final + " " * (last_line_len - len(final)))

def mega_nz_download(session: requests.Session, url: str):
    url_lower = url.lower()
    if "/folder/" in url_lower:
        _mega_nz_folder(session, url)
    elif "/file" in url_lower:
        _mega_nz_single(session, url)
    return None
    # yes i know it doesnt return anything, handle it yourself in your backend, like
    # if url is None and "mega.nz" in user_input_url.lower(): # Reason for skip: Megas module downloads it because mega != direct link.
    #   return
