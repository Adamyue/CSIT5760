"""Record normal and disputed Sepolia flows using temporary role accounts."""

import json
from pathlib import Path

from dotenv import dotenv_values
from web3 import Web3


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/contracts/SafeTradeEscrow.sol/SafeTradeEscrow.json"
MANIFEST_PATH = ROOT / "deployments/sepolia.json"
OUTPUT = ROOT / "evidence/demo-sepolia.json"


def prefixed_hex(value):
    text = value.hex()
    return text if text.startswith("0x") else f"0x{text}"


def fee_fields(w3):
    block = w3.eth.get_block("latest")
    priority = w3.eth.max_priority_fee
    return {
        "maxPriorityFeePerGas": priority,
        "maxFeePerGas": block["baseFeePerGas"] * 2 + priority,
    }


def send(w3, account, transaction):
    transaction.setdefault(
        "nonce", w3.eth.get_transaction_count(account.address, "pending")
    )
    transaction.setdefault("chainId", 11155111)
    transaction.update(fee_fields(w3))
    transaction["gas"] = (w3.eth.estimate_gas(transaction) * 120) // 100
    signed = account.sign_transaction(transaction)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction reverted: {prefixed_hex(tx_hash)}")
    return {
        "hash": prefixed_hex(receipt.transactionHash),
        "blockNumber": receipt.blockNumber,
    }


def call_transaction(w3, account, function, value=0):
    return send(
        w3,
        account,
        function.build_transaction({"from": account.address, "value": value}),
    )


def main():
    config = dotenv_values(ROOT / ".env")
    w3 = Web3(
        Web3.HTTPProvider(config["SEPOLIA_RPC_URL"], request_kwargs={"timeout": 30})
    )
    if not w3.is_connected() or w3.eth.chain_id != 11155111:
        raise RuntimeError("RPC is not connected to Ethereum Sepolia")

    demo_key_names = (
        "DEMO_BUYER_PRIVATE_KEY",
        "DEMO_SELLER_PRIVATE_KEY",
        "DEMO_ARBITER_PRIVATE_KEY",
    )
    if any(not config.get(name) for name in demo_key_names):
        raise RuntimeError(
            "The Sepolia demo requires buyer, seller, and arbiter private keys "
            "in the ignored .env file"
        )

    deployer = w3.eth.account.from_key(config["DEPLOYER_PRIVATE_KEY"])
    buyer, seller, arbiter = (
        w3.eth.account.from_key(config[name]) for name in demo_key_names
    )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    contract = w3.eth.contract(address=manifest["address"], abi=artifact["abi"])

    funding_amount = w3.to_wei("0.003", "ether")
    funding = {}
    for name, account in (
        ("buyer", buyer),
        ("seller", seller),
        ("arbiter", arbiter),
    ):
        funding[name] = send(
            w3,
            deployer,
            {
                "from": deployer.address,
                "to": account.address,
                "value": funding_amount,
            },
        )

    role = contract.functions.ARBITER_ROLE().call()
    arbiter_grant = call_transaction(
        w3, deployer, contract.functions.grantRole(role, arbiter.address)
    )

    latest = w3.eth.get_block("latest")
    deadline = latest["timestamp"] + 6 * 60 * 60
    amount = w3.to_wei("0.001", "ether")

    normal_id = contract.functions.nextEscrowId().call()
    normal = {
        "create": call_transaction(
            w3,
            buyer,
            contract.functions.createEscrow(
                seller.address,
                arbiter.address,
                deadline,
                w3.keccak(text="SafeTrade synthetic normal terms"),
            ),
            amount,
        ),
        "deliver": call_transaction(
            w3,
            seller,
            contract.functions.markDelivered(
                normal_id, w3.keccak(text="SafeTrade synthetic normal delivery")
            ),
        ),
        "release": call_transaction(
            w3, buyer, contract.functions.confirmReceipt(normal_id)
        ),
    }

    disputed_id = contract.functions.nextEscrowId().call()
    disputed = {
        "create": call_transaction(
            w3,
            buyer,
            contract.functions.createEscrow(
                seller.address,
                arbiter.address,
                deadline,
                w3.keccak(text="SafeTrade synthetic disputed terms"),
            ),
            amount,
        ),
        "deliver": call_transaction(
            w3,
            seller,
            contract.functions.markDelivered(
                disputed_id,
                w3.keccak(text="SafeTrade synthetic disputed delivery"),
            ),
        ),
        "dispute": call_transaction(
            w3, buyer, contract.functions.raiseDispute(disputed_id)
        ),
        "resolve": call_transaction(
            w3, arbiter, contract.functions.resolveDispute(disputed_id, 6000)
        ),
    }

    normal["sellerWithdrawal"] = call_transaction(
        w3, seller, contract.functions.withdraw()
    )
    disputed["buyerWithdrawal"] = call_transaction(
        w3, buyer, contract.functions.withdraw()
    )
    disputed["arbiterWithdrawal"] = call_transaction(
        w3, arbiter, contract.functions.withdraw()
    )

    evidence = {
        "network": "sepolia",
        "chainId": "11155111",
        "contract": manifest["address"],
        "deploymentTransactionHash": manifest["deploymentTransactionHash"],
        "accounts": {
            "deployer": deployer.address,
            "buyer": buyer.address,
            "seller": seller.address,
            "arbiter": arbiter.address,
        },
        "accountFunding": funding,
        "arbiterGrant": arbiter_grant,
        "normalFlow": {"escrowId": str(normal_id), **normal},
        "disputedFlow": {"escrowId": str(disputed_id), **disputed},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
