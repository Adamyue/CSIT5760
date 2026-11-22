"""Fallback Sepolia deployment using Python Web3 when Node RPC is unavailable."""

from datetime import datetime, timezone
import json
from pathlib import Path

from dotenv import dotenv_values
from web3 import Web3


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/contracts/SafeTradeEscrow.sol/SafeTradeEscrow.json"
OUTPUT = ROOT / "deployments/sepolia.json"


def fee_fields(w3):
    block = w3.eth.get_block("latest")
    priority = w3.eth.max_priority_fee
    return {
        "maxPriorityFeePerGas": priority,
        "maxFeePerGas": block["baseFeePerGas"] * 2 + priority,
    }


def send(w3, account, transaction):
    transaction["gas"] = (w3.eth.estimate_gas(transaction) * 120) // 100
    signed = account.sign_transaction(transaction)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)


def prefixed_hex(value):
    text = value.hex()
    return text if text.startswith("0x") else f"0x{text}"


def main():
    config = dotenv_values(ROOT / ".env")
    rpc_url = config.get("SEPOLIA_RPC_URL")
    private_key = config.get("DEPLOYER_PRIVATE_KEY")
    arbiter_address = config.get("ARBITER_ADDRESS")
    if not rpc_url or not private_key or not arbiter_address:
        raise RuntimeError(
            "SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY, and ARBITER_ADDRESS are required"
        )

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    if not w3.is_connected() or w3.eth.chain_id != 11155111:
        raise RuntimeError("RPC is not connected to Ethereum Sepolia")

    account = w3.eth.account.from_key(private_key)
    arbiter = Web3.to_checksum_address(arbiter_address)
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])

    nonce = w3.eth.get_transaction_count(account.address, "pending")
    deploy_tx = factory.constructor(account.address).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": 11155111,
            **fee_fields(w3),
        }
    )
    deploy_receipt = send(w3, account, deploy_tx)
    if deploy_receipt.status != 1:
        raise RuntimeError("Contract deployment reverted")

    contract_address = deploy_receipt.contractAddress
    deployment_block = w3.eth.get_block(deploy_receipt.blockNumber)
    manifest = {
        "contract": "SafeTradeEscrow",
        "address": contract_address,
        "network": "sepolia",
        "chainId": "11155111",
        "deployer": account.address,
        "deploymentTransactionHash": prefixed_hex(deploy_receipt.transactionHash),
        "deploymentBlockNumber": deploy_receipt.blockNumber,
        "deploymentTimestamp": datetime.fromtimestamp(
            deployment_block["timestamp"], timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "arbiter": arbiter,
        "arbiterGrantTransactionHash": None,
        "compiler": "0.8.28",
        "optimizer": {"enabled": True, "runs": 200},
        "evmVersion": "cancun",
        "verified": False,
        "etherscanUrl": f"https://sepolia.etherscan.io/address/{contract_address}",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    contract = w3.eth.contract(address=contract_address, abi=artifact["abi"])
    role = contract.functions.ARBITER_ROLE().call()
    grant_tx = contract.functions.grantRole(role, arbiter).build_transaction(
        {
            "from": account.address,
            "nonce": nonce + 1,
            "chainId": 11155111,
            **fee_fields(w3),
        }
    )
    grant_receipt = send(w3, account, grant_tx)
    if grant_receipt.status != 1:
        raise RuntimeError("Arbiter role grant reverted")

    manifest["arbiterGrantTransactionHash"] = prefixed_hex(
        grant_receipt.transactionHash
    )
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
