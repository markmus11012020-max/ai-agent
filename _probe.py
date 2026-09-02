import requests
a_token = "30f3d061d3bdcade60c48b2857446fdb"
urls = [
    "https://www.multitour.ru/api/v2/",
    "https://www.multitour.ru/api/v1/",
    "https://www.multitour.ru/api/",
    "https://api.multitour.ru/v2/",
    "https://api.multitour.ru/",
    "https://www.multitour.ru/api/v2/index.php",
]
for u in urls:
    try:
        r = requests.post(u, json={"header": {"token": a_token, "method": "GetCities"}, "request": []}, timeout=8)
        print(u, r.status_code, r.text[:200])
    except Exception as e:
        print(u, "ERR", str(e)[:80])
