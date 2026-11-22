"""Verify the deployed SafeTrade contract through Etherscan API V2."""

import json
from pathlib import Path
import time

from dotenv import dotenv_values
from eth_abi import encode
import requests


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "deployments/sepolia.json"
BUILD_INFO_DIR = ROOT / "artifacts/build-info"
API_URL = "https://api.etherscan.io/v2/api"


def main():
    config = dotenv_values(ROOT / ".env")
    api_key = config.get("ETHERSCAN_API_KEY")
    if not api_key:
        raise RuntimeError("ETHERSCAN_API_KEY is required")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    build_paths = list(BUILD_INFO_DIR.glob("*.json"))
    if len(build_paths) != 1:
        raise RuntimeError("Expected exactly one Hardhat build-info file")
    build_info = json.loads(build_paths[0].read_text(encoding="utf-8"))

    constructor_arguments = encode(
        ["address"], [manifest["deployer"]]
    ).hex()
    query = {
        "chainid": "11155111",
        "module": "contract",
        "action": "verifysourcecode",
    }
    payload = {
        "apikey": api_key,
        "contractaddress": manifest["address"],
        "sourceCode": json.dumps(build_info["input"], separators=(",", ":")),
        "codeformat": "solidity-standard-json-input",
        "contractname": "contracts/SafeTradeEscrow.sol:SafeTradeEscrow",
        "compilerversion": "v0.8.28+commit.7893614a",
        "constructorArguments": constructor_arguments,
        "licenseType": "3",
    }
    response = requests.post(API_URL, params=query, data=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result.get("status") != "1":
        if "already verified" in str(result.get("result", "")).lower():
            manifest["verified"] = True
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            print("Contract is already verified.")
            return
        raise RuntimeError(f"Etherscan submission failed: {result}")

    guid = result["result"]
    status_query = {
        "chainid": "11155111",
        "module": "contract",
        "action": "checkverifystatus",
        "guid": guid,
        "apikey": api_key,
    }
    for _ in range(24):
        time.sleep(5)
        status_response = requests.get(API_URL, params=status_query, timeout=30)
        status_response.raise_for_status()
        status = status_response.json()
        message = str(status.get("result", ""))
        if status.get("status") == "1":
            manifest["verified"] = True
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            print(message)
            print(f"{manifest['etherscanUrl']}#code")
            return
        if "pending" not in message.lower() and "queue" not in message.lower():
            raise RuntimeError(f"Etherscan verification failed: {status}")
    raise TimeoutError("Etherscan verification remained pending for two minutes")


if __name__ == "__main__":
    main()
