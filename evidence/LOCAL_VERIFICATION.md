# Local Verification Evidence

Final rerun: 22 November 2026 (HKT)

## Compilation

Command: `npm run compile`

Result: 11 Solidity files compiled successfully for Cancun using Solidity
0.8.28. The only compiler warning concerns `selfdestruct` in the test-only
`ForceSender` helper used to validate forced ETH behavior; the production
contract does not use `selfdestruct`.

## Automated tests

Command: `npm test`

Result: **61 passing, 0 failing**.

The suite covers deployment, roles, creation validation, delivery, deadline
boundaries, release, three refund paths, review timeout, disputes, fee/split
boundaries, one-wei rounding, revoked assigned arbiter policy, withdrawals,
rejecting and recursive receivers, liabilities, direct/forced ETH, and pausing.

## Coverage

Command: `npm run coverage`

| Scope | Statements | Branches | Functions | Lines |
|---|---:|---:|---:|---:|
| `SafeTradeEscrow.sol` | 100% | 98.72% | 100% | 100% |
| All contracts including test helpers | 100% | 97.56% | 100% | 100% |

The proposal targets (40 tests, 95% lines, and 90% branches) are exceeded.

## Security analysis

Command: `npm run security`

Slither 0.11.6 analyzed 12 compiled contracts with 100 detectors. Production
results:

- High: 0
- Medium: 0
- Low: 5 timestamp uses
- Informational: 1 intentional low-level withdrawal call

The findings are interpreted in `audit/SECURITY_REPORT.md`; raw JSON is
`evidence/slither-latest.json`.

## Script validation

- `npm run deploy:local`: passed and wrote `deployments/hardhat.json`.
- `npm run demo:local`: passed for normal and disputed flows and wrote
  `evidence/demo-hardhat.json`.
- IDE diagnostics after edits: no linter errors.

## Public deployment status

Initial Sepolia attempts timed out before broadcast. Forcing Node to prefer IPv4
temporarily restored JSON-RPC connectivity and returned chain ID `0xaa36a7`.
After the account was funded, Node RPC remained unreliable, so Python Web3
7.16.0 deployed the identical compiled artifact on 16 November 2026.

- Contract: `0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E`
- Deployment block: 12147762
- Etherscan verification: passed through API V2
- Normal flow: create, delivery, release, and seller withdrawal passed
- Disputed flow: create, delivery, dispute, 60/40 resolution, buyer withdrawal,
  and arbiter withdrawal passed
- Final on-chain state: `nextEscrowId = 3`, `totalLocked = 0`,
  `totalPending = 0`, and the configured arbiter role is active

Authoritative public links are in `deployment/SEPOLIA_DEPLOYMENT.md`; complete
machine-readable receipts are in `deployments/sepolia.json` and
`evidence/demo-sepolia.json`.

## Final public cross-check

On 22 November 2026, a read-only Sepolia check confirmed that the runtime
bytecode at the recorded address exactly matches the current Hardhat artifact.
The contract returned `nextEscrowId = 3`, `totalLocked = 0`, and
`totalPending = 0`. Etherscan API V2 returned `SafeTradeEscrow`, compiler
`v0.8.28+commit.7893614a`, optimization enabled with 200 runs, Cancun EVM, and
the complete verified Standard JSON source.

## Development-dependency audit

`npm audit --audit-level=high` passed after upgrading
`@nomicfoundation/hardhat-verify` to 2.1.4 and overriding vulnerable
`serialize-javascript` and `tmp` transitive versions. The remaining findings
are 8 Moderate and 18 Low issues in the Hardhat 2 / solidity-coverage
development toolchain. npm's proposed full remediation requires breaking
changes to Hardhat 3 or an older coverage package; these tools are not deployed
as an application service.
