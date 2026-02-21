import requests
import time

payload = {
    "prompt": "a cyberpunk hacker cat in the matrix",
    "params": {"n": 1, "width": 512, "height": 512},
    "nsfw": False,
    "censor_nsfw": False,
    "models": ["AlbedoBase XL (SDXL)"]
}
headers = {"apikey": "0000000000", "Client-Agent": "RedPill:1.0:unknown"}

print("Starting generation...")
res = requests.post("https://stablehorde.net/api/v2/generate/async", json=payload, headers=headers).json()
print(res)

if "id" in res:
    uuid = res["id"]
    while True:
        status = requests.get(f"https://stablehorde.net/api/v2/generate/status/{uuid}").json()
        print("Status:", status.get("wait_time"), "Wait:", status.get("waiting"), "Done:", status.get("done"))
        if status.get("done"):
            if "generations" in status:
                print("Generated image URL:", status["generations"][0]["img"])
            else:
                print("No generations?", status)
            break
        time.sleep(3)
