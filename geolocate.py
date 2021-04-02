import requests

f = open("ip4s.csv", "r")
ips = f.read().splitlines()

# geolocating ips
for ip in ips:
    req = requests.get("http://ip-api.com/json/" + ip)
    resp = req.json()
    if "country" in resp:
        print(resp["country"])
    else:
        print("Anon")