from geolocator import geolocate
import requests
import getopt
import sys
import argparse
import subprocess
from time import sleep
import re
import csv

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

    while True:
        if process.poll() is not None:
            break
        print("--Updated Wantlist--")
        print(get_wantlist()["Keys"])
        sleep(5)
        rc = process.poll()

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


# get info on each peer's ledger from the bitswap
def ledger_info(peer):
    req = requests.post(
        "http://127.0.0.1:5001/api/v0/bitswap/ledger", params={"arg": peer}
    )
    return req.json()


# get info on the peer's ipfs node
def id_info(contributors):
    print(f"Geolocating peers, ETA around {len(contributors)*1.5} seconds")
    for count, peer in enumerate(contributors):
        req = requests.post(
            "http://127.0.0.1:5001/api/v0/id", params={"arg": peer["Peer"]}
        )
        resp = req.json()
        addresses = extract_ip4s(resp["Addresses"]) if "Addresses" in resp else []
        peer["Addr"] = addresses
        agent = resp["AgentVersion"] if "AgentVersion" in resp else "Unknown"
        peer["Agent"] = agent

        # try to geolocate the host
        for addr in addresses:
            country = geolocate(addr)
            if country != "Unknown":
                peer["Country"] = country
        # assign unknown if no success (also if there are no addresses to check)
        if country == "Unknown" or len(addresses) == 0:
            peer["Country"] = "Unknown"


# extracts the first ip4 in order to geolocate the peer
def extract_ip4s(addresses):
    ips = []
    pattern = r"((([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])[ (\[]?(\.|dot)[ )\]]?){3}([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5]))"
    for addr in addresses:
        ips.extend([match[0] for match in re.findall(pattern, addr)])

    # convert to a set in order to avoid duplicate addresses for each host
    # then remove localhost
    ip4s = set(ips)
    if "127.0.0.1" in ip4s:
        ip4s.remove("127.0.0.1")
    return list(ip4s)


def get_latencies(contributors):
    latencies = {}
    req = requests.post("http://127.0.0.1:5001/api/v0/swarm/peers?latency=true")
    resp = req.json()
    # get the latencies from the response and put them into a dictionary
    for peer in resp["Peers"]:
        latencies[peer["Peer"]] = peer["Latency"]
    # for each contributor, assign the correct latency
    for contributor in contributors:
        # [:-2] in order to remove the "ms" unit
        if contributor["Peer"] in latencies:
            latency = latencies[contributor["Peer"]][:-2]
        else:
            # placeholder value
            latency = "Nan"
        contributor["Latency"] = latency


def print_infos(contributors):
    print("\n--Recap on each Peer's contribution--")
    print("----")

    # print header
    print(
        f"{'Peer' : <10}{'PeerID' : ^10}{'Country' : ^20}{'Agent' : ^25}{'Latency(ms)' : ^15}{'RecvBytes' : ^10}{'Blocks' : >5}"
    )
    for count, contributor in enumerate(contributors):
        # print deadly table
        print(
            f"{count : <10}{contributor['Peer'][:5]+'...' : ^10}{contributor['Country'] : ^20}{contributor['Agent'][:22]+'...' : ^25}{contributor['Latency'][:10] :^15}{contributor['Recv'] : ^10}{contributor['Exchanged']:>5}"
        )


def main():
    get_cid()
    stats = bitswap_stat()
    peers = stats["Peers"]
    recv_blocks = stats["BlocksReceived"]
    recv_bytes = stats["DataReceived"]
    dup_blocks = stats["DupBlksReceived"]
    dup_bytes = stats["DupDataReceived"]
    legit_blocks = recv_blocks - dup_blocks
    legit_bytes = recv_bytes - dup_bytes

    print("\n--Bitswap stats regarding the transfer--")
    print(f"Received a total of {recv_blocks} blocks ({recv_bytes} bytes)")
    print(
        f"Duplicate blocks account for ({dup_blocks / recv_blocks * 100 :.2f}, % of the total"
    )
    print(
        f"Duplicate bytes account for ({dup_bytes / recv_bytes * 100 :.2f}, % of the total"
    )
    print(f"Received {legit_blocks} non-duplicate blocks")
    print(f"Received {legit_bytes} non-duplicate bytes")
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

    # get latencies from all the swarm and set the correct latency to each contributor
    latencies = get_latencies(contributors)

    # print final infos on each contributor
    print_infos(contributors, legit_bytes)

    # logging enabled
    if args.l:
        print("You can find more logs in the current directory")
        # write logs about peers
        with open(
            str(args.c) + "_peers.csv", "w", encoding="utf8", newline=""
        ) as output_file:
            fc = csv.DictWriter(
                output_file,
                fieldnames=contributors[0].keys(),
            )
            fc.writeheader()
            fc.writerows(contributors)
        # write logs about bitswap


if __name__ == "__main__":
    # add the arguments to the parser and parse them
    parser = argparse.ArgumentParser(
        description="Analyze ipfs' bitswap behaviour when downloading a CID. Requires a running ipfs daemon!"
    )
    parser.add_argument("-c", help="The CID to be downloaded", required=True)
    parser.add_argument(
        "-p",
        help="The relative path where the CID will be stored. If not set, defaults to ./downloads/",
        type=str,
        default="./downloads/",
    )
    parser.add_argument(
        "-l",
        help="If set, logs statistics about the bitswap and the peers",
        action="store_true",
    )
    args = parser.parse_args()

    main()
