# Sepolia Deployment Record

## Configuration

- Network: Ethereum Sepolia
- Chain ID: 11155111
- Contract: `SafeTradeEscrow`
- Compiler: Solidity 0.8.28
- EVM version: Cancun
- Optimizer: enabled, 200 runs
- Constructor argument: deployer/administrator address

## Public evidence

| Item | Value |
|---|---|
| Contract address | `0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E` |
| Deployer address | `0x84773c4dA4B711f38a0Fe524Fad5Ed07bb0C6F4E` |
| Deployment transaction | [0x631166…d045a](https://sepolia.etherscan.io/tx/0x6311661fc5b586ee4ac5ccf58c99f498ef5f691304e785c407bd8a42be3d045a) |
| Deployment block | 12147762 |
| Deployment date/time | 16 November 2026, 21:57:12 HKT (13:57:12 UTC) |
| Configured arbiter | `0x9fFDd622766f99d71b17bD3c7fDB9259daABf9aA` |
| Arbiter grant transaction | [0x629f66…22fc0](https://sepolia.etherscan.io/tx/0x629f665d6a4460d969e3fbeb3e18a8e780dd8fa6f69c623f66321d3bbee22fc0) |
| Verified Etherscan source | [SafeTradeEscrow verified code](https://sepolia.etherscan.io/address/0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E#code) |
| Normal create transaction | [0x0d9fab…77dc6](https://sepolia.etherscan.io/tx/0x0d9fab02a029e9ba2ba8e5f223b607da2da1e372d1919c6379e349a1d0577dc6) |
| Normal delivery transaction | [0x717b4f…80f69](https://sepolia.etherscan.io/tx/0x717b4fffff1c9a851044277267540c4115d37fc9c8cf6f9204480edbe8280f69) |
| Normal release transaction | [0xe98a7b…04f4e](https://sepolia.etherscan.io/tx/0xe98a7ba81ea98922f164272516beb0a678395eebfba2480e967d06f560e04f4e) |
| Disputed create transaction | [0x9faf79…fc2a7](https://sepolia.etherscan.io/tx/0x9faf79d91dc339645cd95814f5d22f592d28ead9f6c9dc708ed73556de9fc2a7) |
| Dispute transaction | [0x2fc7d0…7da67](https://sepolia.etherscan.io/tx/0x2fc7d04454ee6986a31151da22c614c1943150df7101fdad841f4e2ae747da67) |
| Resolution transaction | [0x69dd16…d4b22](https://sepolia.etherscan.io/tx/0x69dd163777fd21c032aa02f2db9b94e7b9ac5fe60eb5bd9866725c70e62d4b22) |
| Seller withdrawal | [0x93ce10…0f304](https://sepolia.etherscan.io/tx/0x93ce10b0a9783039d9c26e109fd9169e36c2850f0d07f512b90397a03390f304) |
| Buyer withdrawal | [0x98423f…f0558](https://sepolia.etherscan.io/tx/0x98423f3a1009d1b0ff063dc376fc834d0ab444525d10e5cac44e82f2748f0558) |
| Demo arbiter withdrawal | [0x206f91…fb2d1](https://sepolia.etherscan.io/tx/0x206f9172209d4b90d91926c6d4d5280aaabdac26b9337dd574f43a0ea4ffb2d1) |

## Attempt record

On 15 November 2026, initial attempts through the configured Alchemy endpoint
and `ethereum-sepolia-rpc.publicnode.com` timed out before broadcast. Setting
Node to prefer IPv4 restored connectivity and confirmed chain ID `0xaa36a7`.
The deployment signer was
`0x84773c4dA4B711f38a0Fe524Fad5Ed07bb0C6F4E`. The final attempt stopped during
estimation because the account held approximately 0.00215 Sepolia ETH while the
estimated transaction required approximately 0.01071 ETH. No transaction was
broadcast during those attempts.

After the account was funded, Node's HTTP client remained unable to reach the
RPC reliably. On 16 November 2026, the same compiled artifact was therefore
deployed through Python Web3 7.16.0. Etherscan API V2 verified the exact
Standard JSON build, and scripted normal and disputed flows completed. The
machine-readable authoritative records are `deployments/sepolia.json` and
`evidence/demo-sepolia.json`.
