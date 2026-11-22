// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// @dev Test-only helper proving forced ETH is excess, not an accounting liability.
contract ForceSender {
    constructor() payable {}

    function forceSend(address payable recipient) external {
        selfdestruct(recipient);
    }
}
