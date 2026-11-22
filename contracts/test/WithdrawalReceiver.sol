// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

interface ISafeTradeEscrow {
    function markDelivered(uint256 escrowId, bytes32 deliveryHash) external;
    function withdraw() external;
}

/// @dev Test helper used to exercise rejecting recipients and recursive withdrawal.
contract WithdrawalReceiver {
    ISafeTradeEscrow public immutable escrow;
    bool public rejectPayment;
    bool public attemptReentry;
    uint256 public receiveCount;

    constructor(address escrowAddress) {
        escrow = ISafeTradeEscrow(escrowAddress);
    }

    function configure(bool reject, bool reenter) external {
        rejectPayment = reject;
        attemptReentry = reenter;
    }

    function markDelivered(uint256 escrowId, bytes32 deliveryHash) external {
        escrow.markDelivered(escrowId, deliveryHash);
    }

    function withdrawFromEscrow() external {
        escrow.withdraw();
    }

    receive() external payable {
        receiveCount++;
        if (rejectPayment) revert("payment rejected");
        if (attemptReentry) {
            try escrow.withdraw() {} catch {}
        }
    }
}
