# Important Test-Case Record

Environment: Hardhat in-process network, Solidity 0.8.28, ethers 6.17.0.
Synthetic hashes and test ETH are used. “Actual result” is updated from the
final automated run; full executable steps are in
`test/SafeTradeEscrow.test.js`.

| ID | Purpose | Preconditions | Input / steps | Expected result | Actual result | Status |
|---|---|---|---|---|---|---|
| TC-01 | Create escrow | Eligible arbiter; distinct accounts | Buyer creates with 1 ETH and valid deadline/hash | `Funded`; event; locked=1 ETH | Automated assertion passed | Pass |
| TC-02 | Reject zero funding | None | Create with 0 ETH | `ZeroAmount` | Automated assertion passed | Pass |
| TC-03 | Reject invalid participants | None | Zero or duplicate buyer/seller/arbiter | `InvalidAddress` | Automated assertions passed | Pass |
| TC-04 | Require eligible arbiter | Arbiter has no role | Create escrow | `NotAuthorized` | Automated assertion passed | Pass |
| TC-05 | Minimum window boundary | Eligible arbiter | Deadline exactly 1 hour from mined block | Creation succeeds | Automated assertion passed | Pass |
| TC-06 | Below minimum window | Eligible arbiter | Deadline less than 1 hour | `DeliveryWindowTooShort` | Automated assertion passed | Pass |
| TC-07 | Maximum window boundary | Eligible arbiter | Deadline exactly 90 days | Creation succeeds | Automated assertion passed | Pass |
| TC-08 | Above maximum window | Eligible arbiter | Deadline over 90 days | `DeliveryWindowTooLong` | Automated assertion passed | Pass |
| TC-09 | Mark delivery | Funded escrow; seller caller | Submit nonzero evidence hash before deadline | `Delivered`; review deadline/event | Automated assertion passed | Pass |
| TC-10 | Reject false delivery caller | Funded escrow | Buyer marks delivery | `NotAuthorized` | Automated assertion passed | Pass |
| TC-11 | Delivery before deadline | Funded escrow | Mark at deadline−1 | Success | Automated assertion passed | Pass |
| TC-12 | Delivery at deadline | Funded escrow | Mark at deadline | `DeliveryDeadlinePassed` | Automated assertion passed | Pass |
| TC-13 | Buyer timeout | Undelivered escrow | Claim at delivery deadline | Full buyer credit; `Refunded` | Automated assertion passed | Pass |
| TC-14 | Normal release | Delivered escrow | Buyer confirms receipt | Full seller credit; `Released` | Automated assertion passed | Pass |
| TC-15 | Voluntary refund | Funded/Delivered/Disputed | Seller refunds | Full buyer credit; no fee | Automated assertions passed | Pass |
| TC-16 | Raise dispute | Delivered; before review expiry | Buyer disputes | `Disputed`; event | Automated assertion passed | Pass |
| TC-17 | Dispute at expiry | Delivered | Dispute at review deadline | `ReviewDeadlinePassed` | Automated assertion passed | Pass |
| TC-18 | Seller review timeout | Delivered; no dispute | Claim at review deadline | Full seller credit; `Released` | Automated assertion passed | Pass |
| TC-19 | Buyer releases dispute | Disputed | Buyer confirms | Full seller credit; `Released` | Automated assertion passed | Pass |
| TC-20 | Arbiter 25/75 split | Disputed | Assigned arbiter resolves at 2500 bps | 1% fee; remaining split; sum conserved | Automated assertion passed | Pass |
| TC-21 | Split lower boundary | Disputed | Resolve at 0 bps | All post-fee value to seller | Automated assertion passed | Pass |
| TC-22 | Split upper boundary | Disputed | Resolve at 10000 bps | All post-fee value to buyer | Automated assertion passed | Pass |
| TC-23 | Invalid split | Disputed | Resolve at 10001 bps | `InvalidShare` | Automated assertion passed | Pass |
| TC-24 | One-wei rounding | 1 wei disputed escrow | Resolve at 5000 bps | Fee/buyer round to 0; seller gets 1 | Automated assertion passed | Pass |
| TC-25 | Unassigned arbiter | Disputed; another eligible arbiter | Other arbiter resolves | `NotAuthorized` | Automated assertion passed | Pass |
| TC-26 | Revoked assigned arbiter | Disputed; role revoked after creation | Assigned arbiter resolves | Success under fixed assignment policy | Automated assertion passed | Pass |
| TC-27 | Pull withdrawal | Seller has credit | Seller withdraws | Credit/pending zero; event | Automated assertion passed | Pass |
| TC-28 | Recursive receiver | Malicious seller has credit | Receive callback calls withdraw again | Exactly one payment | Automated assertion passed | Pass |
| TC-29 | Rejecting receiver | Reverting seller has credit | Attempt withdrawal | `TransferFailed`; credit preserved | Automated assertion passed | Pass |
| TC-30 | Accounting invariant | Mixed locked/settled escrows | Inspect balance and liabilities | Balance ≥ locked + pending | Automated assertion passed | Pass |
| TC-31 | Pause admission | Existing delivered escrow; paused | Create new; settle old; withdraw | New create fails; exits succeed | Automated assertion passed | Pass |
| TC-32 | Direct payment | Deployed contract | Send ETH to receive/fallback | `DirectPaymentNotAllowed` | Automated assertions passed | Pass |
| TC-33 | Forced ETH | Deployed contract | `selfdestruct` helper sends ETH | Excess balance; liabilities unchanged | Automated assertion passed | Pass |
| TC-34 | Duplicate settlement | Released/refunded escrow | Repeat operation | `InvalidState` | Automated assertions passed | Pass |
| TC-35 | Unauthorized role admin | Non-admin account | Grant role | AccessControl revert | Automated assertion passed | Pass |

Screenshots, if included in the final package, are supplementary. The test
source and console output are the primary reproducible evidence.
