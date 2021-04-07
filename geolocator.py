import requests
from time import sleep

# geolocates an ip address returning its country as a string
def geolocate(ip, polite=True):
    if polite:
        sleep(1.35)
    resp = requests.get("http://ip-api.com/json/" + ip).json()
    return resp["country"] if "country" in resp else "Unknown"
    # polite if we have more than 45 peers to geolocate
    # free api limited to 45 reqs/min