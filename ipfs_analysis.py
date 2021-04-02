import requests, pprint as pp
import re
import csv

# endpoints
base = "http://localhost:5001/api/v0/"
get = base + "get"
stat = base + "bitswap/stat"
ledger = base + "bitswap/ledger"
id = base + "id"

print("-------")
print("Getting file from ipfs")
print("-------")
# get old internet files
## req = requests.post(get, params={"arg": "QmbsZEvJE8EU51HCUHQg2aem9JNFmFHdva3tGVYutdCXHp"})

# get info from the bitswap about connected partners
req = requests.post(stat, params={"human": "true", "verbose": "true"})
resp = req.json()
partners = resp["Peers"]

# query each partner's ledger
peers = []
for peer in partners:
    req = requests.post(ledger, params={"arg": peer})
    peers.append(req.json())

print("-------")
print("Peers from which we received something: ")
print("-------")
# only consider peers from which we received something
filtered_peers = list(filter(lambda x: x["Recv"] > 0, peers))
pp.pprint(filtered_peers)

print("-------")
print("Info on Those peers")
print("-------")
# get info on the nodes from which we received something
node_infos = []
for node in filtered_peers:
    req = requests.post(id, params={"arg": node["Peer"]})
    node_infos.append(req.json())

pp.pprint(node_infos)

print("-------")
print("Protocol and agent version: ")
print("-------")
# check the protocol and agent version used by the peers
protoagent_version = [(x["ProtocolVersion"], x["AgentVersion"]) for x in node_infos]
pp.pprint(protoagent_version)

## extract ip4s using regex
addresses = [x["Addresses"] for x in node_infos]
pattern = r"((([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])[ (\[]?(\.|dot)[ )\]]?){3}([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5]))"
ip4s = []
for node in addresses:
    for ips in node:
        ip4s.extend([match[0] for match in re.findall(pattern, ips)])

ip4s = set(ip4s)
ip4s.remove("127.0.0.1")

print(list(ip4s))

with open("ip4s.csv", "w") as file:
    writer = csv.writer(file)
    for item in ip4s:
        writer.writerow([item])
