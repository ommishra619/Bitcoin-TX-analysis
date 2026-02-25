import requests

BASE_URL = "https://blockstream.info/api"

def get_address_info(address):
    url = f"{BASE_URL}/address/{address}"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Error fetching address data")

    return response.json()


def get_address_txs(address):
    url = f"{BASE_URL}/address/{address}/txs"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Error fetching transactions")

    return response.json()
