// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title SafeTradeEscrow
/// @notice Holds ETH for deadline-based buyer/seller trades and optional arbitration.
contract SafeTradeEscrow is AccessControl, Pausable, ReentrancyGuard {
    bytes32 public constant ARBITER_ROLE = keccak256("ARBITER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    uint256 public constant ARBITER_FEE_BPS = 100;
    uint256 public constant BPS_DENOMINATOR = 10_000;
    uint256 public constant REVIEW_PERIOD = 3 days;
    uint256 public constant MIN_DELIVERY_WINDOW = 1 hours;
    uint256 public constant MAX_DELIVERY_WINDOW = 90 days;

    enum State {
        None,
        Funded,
        Delivered,
        Disputed,
        Released,
        Refunded,
        Resolved
    }

    struct Escrow {
        address buyer;
        address seller;
        address arbiter;
        uint256 amount;
        uint256 deliveryDeadline;
        uint256 reviewDeadline;
        State state;
        bytes32 termsHash;
        bytes32 deliveryHash;
    }

    uint256 public nextEscrowId = 1;
    uint256 public totalLocked;
    uint256 public totalPending;

    mapping(uint256 escrowId => Escrow escrow) private _escrows;
    mapping(address account => uint256 amount) public pendingWithdrawals;

    error EscrowNotFound(uint256 escrowId);
    error NotAuthorized();
    error InvalidState(State current);
    error InvalidAddress();
    error InvalidHash();
    error ZeroAmount();
    error DeliveryWindowTooShort();
    error DeliveryWindowTooLong();
    error DeliveryDeadlinePassed();
    error DeliveryDeadlineNotReached();
    error ReviewDeadlinePassed();
    error ReviewDeadlineNotReached();
    error InvalidShare();
    error NothingToWithdraw();
    error TransferFailed();
    error DirectPaymentNotAllowed();

    event EscrowCreated(
        uint256 indexed escrowId,
        address indexed buyer,
        address indexed seller,
        address arbiter,
        uint256 amount,
        uint256 deliveryDeadline,
        bytes32 termsHash
    );
    event DeliveryMarked(
        uint256 indexed escrowId,
        bytes32 deliveryHash,
        uint256 reviewDeadline
    );
    event DisputeRaised(uint256 indexed escrowId);
    event DisputeResolved(
        uint256 indexed escrowId,
        uint256 buyerAmount,
        uint256 sellerAmount,
        uint256 arbiterFee
    );
    event PaymentReleased(uint256 indexed escrowId, uint256 amount);
    event EscrowRefunded(uint256 indexed escrowId, uint256 amount);
    event Withdrawal(address indexed account, uint256 amount);

    constructor(address administrator) {
        if (administrator == address(0)) revert InvalidAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, administrator);
        _grantRole(PAUSER_ROLE, administrator);
    }

    /// @notice Creates and funds an escrow. The caller becomes the buyer.
    function createEscrow(
        address seller,
        address arbiter,
        uint256 deliveryDeadline,
        bytes32 termsHash
    ) external payable whenNotPaused returns (uint256 escrowId) {
        if (msg.value == 0) revert ZeroAmount();
        if (seller == address(0) || arbiter == address(0)) revert InvalidAddress();
        if (
            seller == msg.sender ||
            arbiter == msg.sender ||
            seller == arbiter
        ) revert InvalidAddress();
        if (termsHash == bytes32(0)) revert InvalidHash();
        if (!hasRole(ARBITER_ROLE, arbiter)) revert NotAuthorized();

        uint256 window = deliveryDeadline > block.timestamp
            ? deliveryDeadline - block.timestamp
            : 0;
        if (window < MIN_DELIVERY_WINDOW) revert DeliveryWindowTooShort();
        if (window > MAX_DELIVERY_WINDOW) revert DeliveryWindowTooLong();

        escrowId = nextEscrowId++;
        _escrows[escrowId] = Escrow({
            buyer: msg.sender,
            seller: seller,
            arbiter: arbiter,
            amount: msg.value,
            deliveryDeadline: deliveryDeadline,
            reviewDeadline: 0,
            state: State.Funded,
            termsHash: termsHash,
            deliveryHash: bytes32(0)
        });
        totalLocked += msg.value;

        emit EscrowCreated(
            escrowId,
            msg.sender,
            seller,
            arbiter,
            msg.value,
            deliveryDeadline,
            termsHash
        );
    }

    /// @notice Records delivery evidence and starts the fixed review period.
    function markDelivered(uint256 escrowId, bytes32 deliveryHash) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.seller) revert NotAuthorized();
        if (escrow.state != State.Funded) revert InvalidState(escrow.state);
        if (block.timestamp >= escrow.deliveryDeadline) {
            revert DeliveryDeadlinePassed();
        }
        if (deliveryHash == bytes32(0)) revert InvalidHash();

        escrow.deliveryHash = deliveryHash;
        escrow.reviewDeadline = block.timestamp + REVIEW_PERIOD;
        escrow.state = State.Delivered;
        emit DeliveryMarked(escrowId, deliveryHash, escrow.reviewDeadline);
    }

    /// @notice Releases all funds to the seller, including from a disputed state.
    function confirmReceipt(uint256 escrowId) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.buyer) revert NotAuthorized();
        if (
            escrow.state != State.Delivered &&
            escrow.state != State.Disputed
        ) revert InvalidState(escrow.state);

        uint256 amount = escrow.amount;
        _settle(escrow, State.Released);
        _credit(escrow.seller, amount);
        emit PaymentReleased(escrowId, amount);
    }

    /// @notice Raises a dispute during the review period.
    function raiseDispute(uint256 escrowId) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.buyer) revert NotAuthorized();
        if (escrow.state != State.Delivered) revert InvalidState(escrow.state);
        if (block.timestamp >= escrow.reviewDeadline) {
            revert ReviewDeadlinePassed();
        }

        escrow.state = State.Disputed;
        emit DisputeRaised(escrowId);
    }

    /// @notice Lets the seller refund the buyer before final settlement.
    function refundBySeller(uint256 escrowId) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.seller) revert NotAuthorized();
        if (
            escrow.state != State.Funded &&
            escrow.state != State.Delivered &&
            escrow.state != State.Disputed
        ) revert InvalidState(escrow.state);

        uint256 amount = escrow.amount;
        _settle(escrow, State.Refunded);
        _credit(escrow.buyer, amount);
        emit EscrowRefunded(escrowId, amount);
    }

    /// @notice Lets the buyer reclaim funds if delivery was not marked in time.
    function claimRefundAfterDeadline(uint256 escrowId) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.buyer) revert NotAuthorized();
        if (escrow.state != State.Funded) revert InvalidState(escrow.state);
        if (block.timestamp < escrow.deliveryDeadline) {
            revert DeliveryDeadlineNotReached();
        }

        uint256 amount = escrow.amount;
        _settle(escrow, State.Refunded);
        _credit(escrow.buyer, amount);
        emit EscrowRefunded(escrowId, amount);
    }

    /// @notice Lets the seller claim payment after an undisputed review period.
    function claimPaymentAfterReview(uint256 escrowId) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.seller) revert NotAuthorized();
        if (escrow.state != State.Delivered) revert InvalidState(escrow.state);
        if (block.timestamp < escrow.reviewDeadline) {
            revert ReviewDeadlineNotReached();
        }

        uint256 amount = escrow.amount;
        _settle(escrow, State.Released);
        _credit(escrow.seller, amount);
        emit PaymentReleased(escrowId, amount);
    }

    /// @notice Splits a disputed escrow. Role revocation does not replace its assigned arbiter.
    function resolveDispute(
        uint256 escrowId,
        uint256 buyerShareBps
    ) external {
        Escrow storage escrow = _getEscrow(escrowId);
        if (msg.sender != escrow.arbiter) revert NotAuthorized();
        if (escrow.state != State.Disputed) revert InvalidState(escrow.state);
        if (buyerShareBps > BPS_DENOMINATOR) revert InvalidShare();

        uint256 amount = escrow.amount;
        uint256 fee = (amount * ARBITER_FEE_BPS) / BPS_DENOMINATOR;
        uint256 distributable = amount - fee;
        uint256 buyerAmount =
            (distributable * buyerShareBps) /
            BPS_DENOMINATOR;
        uint256 sellerAmount = distributable - buyerAmount;

        _settle(escrow, State.Resolved);
        _credit(escrow.buyer, buyerAmount);
        _credit(escrow.seller, sellerAmount);
        _credit(escrow.arbiter, fee);
        emit DisputeResolved(escrowId, buyerAmount, sellerAmount, fee);
    }

    /// @notice Withdraws the caller's accumulated pull-payment balance.
    function withdraw() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        if (amount == 0) revert NothingToWithdraw();

        pendingWithdrawals[msg.sender] = 0;
        totalPending -= amount;
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        if (!success) revert TransferFailed();
        emit Withdrawal(msg.sender, amount);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    function getEscrow(
        uint256 escrowId
    ) external view returns (Escrow memory) {
        Escrow storage escrow = _getEscrow(escrowId);
        return escrow;
    }

    function _getEscrow(
        uint256 escrowId
    ) private view returns (Escrow storage escrow) {
        escrow = _escrows[escrowId];
        if (escrow.state == State.None) revert EscrowNotFound(escrowId);
    }

    function _settle(Escrow storage escrow, State finalState) private {
        escrow.state = finalState;
        totalLocked -= escrow.amount;
        totalPending += escrow.amount;
    }

    function _credit(address account, uint256 amount) private {
        pendingWithdrawals[account] += amount;
    }

    receive() external payable {
        revert DirectPaymentNotAllowed();
    }

    fallback() external payable {
        revert DirectPaymentNotAllowed();
    }
}
