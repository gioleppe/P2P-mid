from geolocator import geolocate
import requests
import getopt
import sys
import argparse
import subprocess
from time import sleep
import re

# uses the CLI interface in order to download a CID to the given path
def get_cid():
    print("Downloading to " + (str(args.p) if args.p else "standard repo"))
    print(
        "This might take a while. Grab a beer and enjoy! (or try with a smaller file)"
    )

    # building the command
    cmd = ["ipfs", "get", args.c]
    if args.p:
        cmd.extend(["-o", args.p])

    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)
    sleep(1)
    # poll the process in order to get the output
    count = 1
    while True:
        if process.poll() is not None:
            break
        print("--Updated Wantlist--")
        print(get_wantlist()["Keys"])
        rc = process.poll()
        sleep(3)

    print("Finished downloading CID " + args.c)


# used to periodically poll the wantlist
def get_wantlist():
    req = requests.post("http://127.0.0.1:5001/api/v0/bitswap/wantlist")
    return req.json()


# get stats on the bitswap
def bitswap_stat():
    req = requests.post(
        "http://127.0.0.1:5001/api/v0/bitswap/stat",
        params={"human": "true", "verbose": "true"},
    )
    return req.json()


# get info on each peer's lefger from the bitswap
def ledger_info(peer):
    req = requests.post(
        "http://127.0.0.1:5001/api/v0/bitswap/ledger", params={"arg": peer}
    )
    return req.json()


# get info on the peer's ipfs node
def id_info(contributors):
    for peer in contributors:
        req = requests.post(
            "http://127.0.0.1:5001/api/v0/id", params={"arg": peer["Peer"]}
        )
        resp = req.json()
        address = extract_ip4(resp["Addresses"])
        peer["Addr"] = address

        # try to geolocate the host
        for addr in address:
            country = geolocate(addr, polite=True)
            if country != "Unknown":
                peer["Country"] = country
        # assign unknown if no success
        if country == "Unknown":
            peer["Country"] = "Unknown"


# extracts the first ip4 in order to geolocate the peer
def extract_ip4(addresses):
    ips = []
    pattern = r"((([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])[ (\[]?(\.|dot)[ )\]]?){3}([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5]))"
    for addr in addresses:
        ips.extend([match[0] for match in re.findall(pattern, addr)])

    # convert to a set in order to avoid duplicate addresses for each host
    # then remove localhost
    ip4s = set(ips)
    ip4s.remove("127.0.0.1")
    return list(ip4s)


def main():
    print("test", args)
    get_cid()
    stats = bitswap_stat()
    peers = stats["Peers"]
    recv_blocks = stats["BlocksReceived"]
    recv_bytes = stats["DataReceived"]

    print("--Bitswap stats regarding the transfer--")
    print(f"Received a total of {recv_blocks} blocks ({recv_bytes} bytes)")
    print(f"At the moment there are {len(peers)} peers in the swarm")

    # query each partner's bitswap ledger
    # in order to get useful infos
    peers_info = []
    for peer in peers:
        peers_info.append(ledger_info(peer))

    contributors = list(filter(lambda x: x["Recv"] > 0, peers_info))
    # percentage of the contributors on the total size of the swarm
    percentage = len(contributors) / len(peers) * 100.0
    print(
        f"{len(contributors)} peers contributed to the download of the file ({percentage:.2f}% of the swarm)"
    )

    # extract more info using ipfs id
    id_info(contributors)
    print(contributors)


if __name__ == "__main__":
    # add the arguments to the parser and parse them
    parser = argparse.ArgumentParser(
        description="Analyze ipfs' bitswap behaviour when downloading a CID. Requires a running ipfs daemon!"
    )
    parser.add_argument("-c", help="The CID to be downloaded", required=True)
    parser.add_argument(
        "-p",
        help="The relative path where the CID will be stored. If not set, defaults to ./downloads",
        type=str,
        default="./downloads",
    )
    args = parser.parse_args()

    main()
