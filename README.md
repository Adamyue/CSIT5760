# SafeTrade: Smart-Contract Escrow with Delivery and Review Deadlines

- **Student:** YUE Pu
- **Student ID:** 20944719
- **Network:** Ethereum Sepolia (chain ID 11155111)

SafeTrade holds ETH between a buyer and seller until delivery is accepted, a
deadline expires, or an assigned arbiter resolves a dispute. It uses pull
payments, explicit state transitions, role-based administration, and admission
pausing. Trade descriptions and delivery evidence remain off-chain; only their
hashes are stored.

## Prerequisites and exact versions

- Node.js 22.17.1 and npm 11.7.0
- Solidity 0.8.28, Cancun EVM, optimizer enabled with 200 runs
- Hardhat 2.29.2
- ethers 6.17.0
- OpenZeppelin Contracts 5.6.1
- Hardhat plugins: ethers 3.1.2, Chai matchers 2.1.2, network helpers
  1.1.2, and verify 2.1.4
- solidity-coverage 0.8.17, Chai 4.5.0, and dotenv 17.2.3
- Python 3.12; Web3 7.16.0 and other Python dependencies pinned in
  `requirements.txt`; Slither 0.11.6

The proposal named Hardhat 3.21.2, but `solidity-coverage` 0.8.17 supports
Hardhat 2 only. Hardhat 2.29.2 is therefore used so the required coverage
evidence is reproducible. This does not change the contract bytecode settings.

## Install, compile, and test

```powershell
npm ci
pip install -r requirements.txt
npm run compile
npm test
npm run coverage
```

Run the complete local verification workflow with:

```powershell
npm run verify:workflow
```

Generated build, dependency, cache, and coverage directories are intentionally
excluded from submission.

## Roles and state model

- **Buyer:** creates/funds an escrow, confirms receipt, disputes during review,
  or claims a refund after missed delivery.
- **Seller:** marks delivery, refunds voluntarily, or claims payment after an
  undisputed review period.
- **Assigned arbiter:** resolves only its assigned disputed escrow. It selects
  the buyer's share and receives a 1% fee.
- **Administrator:** grants/revokes role eligibility; it cannot settle or
  redirect escrowed funds.
- **Pauser:** pauses only new escrow creation. Existing exits and withdrawals
  remain available.

States are `Funded`, `Delivered`, `Disputed`, `Released`, `Refunded`, and
`Resolved`, plus the `None` sentinel. Delivery is valid before
`deliveryDeadline`; timeout starts at that timestamp. The seller's three-day
review timeout starts when delivery is marked.

## Local demonstration

```powershell
npm run demo:local
```

The script deploys a local instance and records both normal and disputed flows
in `evidence/demo-hardhat.json`.

## Sepolia deployment and verification

1. Copy `.env.example` to `.env`.
2. Set `SEPOLIA_RPC_URL`, `DEPLOYER_PRIVATE_KEY`, `ETHERSCAN_API_KEY`, and
   `ARBITER_ADDRESS`. To rerun a public demo, also set all three
   `DEMO_*_PRIVATE_KEY` values. Never commit `.env`.
3. Fund only the required test accounts with Sepolia ETH.
4. Run the Hardhat route, or use the Python Web3 fallback if Node RPC
   connectivity is unavailable:

```powershell
npm run deploy:sepolia
# Fallback used for the recorded deployment:
npm run deploy:sepolia:web3
npm run verify:etherscan
```

The script writes the address, deployment transaction, block number, compiler
settings, and arbiter grant transaction to `deployments/sepolia.json`. When an
Etherscan API key is configured, it waits five confirmations and verifies the
source automatically.

To record normal and disputed public flows, use either route below. Both routes
require the three test-only demo accounts configured in the ignored `.env`,
fund them, complete both flows, and withdraw all escrow credits. Requiring
recoverable accounts avoids stranding test ETH if an RPC or process fails.

```powershell
npm run demo:sepolia
npm run demo:sepolia:web3
```

The verified deployment is:

- Contract: `0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E`
- Block: 12147762
- Deployment time: 16 November 2026, 21:57:12 HKT (13:57:12 UTC)
- [Verified Etherscan source](https://sepolia.etherscan.io/address/0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E#code)

All deployment and flow transaction links are recorded in
`deployment/SEPOLIA_DEPLOYMENT.md`.

## Contract interaction

1. Administrator grants `ARBITER_ROLE` to a vetted arbiter.
2. Buyer computes a terms hash and calls payable `createEscrow`.
3. Seller checks all terms and calls `markDelivered` with an evidence hash.
4. Buyer calls `confirmReceipt`, or disputes with `raiseDispute`.
5. If disputed, the assigned arbiter calls `resolveDispute(id, buyerShareBps)`.
6. Each credited party independently calls `withdraw`.

`buyerShareBps` is 0–10,000 and applies to the balance after the 1% arbitration
fee. A seller refund never charges a fee.

## Security analysis

```powershell
npm run security
```

The raw Slither result is written to `evidence/slither-latest.json`; interpreted
findings, remediation, retesting, and residual risks are documented in
`audit/SECURITY_REPORT.md`.

Key controls include checks-effects-interactions, `ReentrancyGuard`, pull
payments, exact participant checks, input validation, terminal states, deadline
boundary rules, and an accounting invariant:

```text
contract balance >= totalLocked + totalPending
```

## Known limitations

- Arbitration is trusted and a non-responsive assigned arbiter can delay a
  disputed settlement while the parties disagree.
- Revoking arbiter eligibility blocks new assignment but intentionally does not
  alter authority for an existing escrow.
- Timestamps have normal validator tolerance; hour/day windows limit impact.
- Hashes prove that content has not changed, not that it is true or private.
- Forced ETH remains unallocated excess.
- ETH only; no ERC-20, NFT, oracle, upgradeability, or production front end.

## Third-party code

OpenZeppelin `AccessControl`, `Pausable`, and `ReentrancyGuard` are used under
their published license. Hardhat and ethers provide development/deployment
support.
