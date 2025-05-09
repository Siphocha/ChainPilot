// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Base} from "../base/Base.sol";

/**
 * @author @0xJonaseb11
 * @title ChainPilot - Payments Module
 * @notice Handles single and batch ETH/ERC20 transfers with gas optimizations.
 * @dev Inherits from Base.sol for shared utilities (e.g., error handling, access control).
 */
contract PaymentsModule is Base {
    // ------------------------ Custom Errors ------------------------
    error InvalidPaymentAmount();
    error TransferFailed();
    error UnauthorizedBatch();

    // ------------------------ Events ------------------------
    event SinglePaymentSent(
        address indexed sender,
        address indexed recipient,
        uint256 amount
    );
    event BatchPaymentSent(
        address indexed sender,
        uint256 totalAmount,
        uint256 recipientCount
    );

    // ------------------------ Constructor ------------------------
    constructor(address _owner) Base(_owner) {}

    // ------------------------ External Functions ------------------------

    /**
     * @notice Send ETH to a single recipient.
     * @param recipient Address to receive ETH.
     * @param amount Amount in wei.
     */
    function sendETH(
        address recipient,
        uint256 amount
    ) external payable {
        if (amount == 0 || msg.value != amount) revert InvalidPaymentAmount();
        
        (bool success, ) = recipient.call{value: amount}("");
        if (!success) revert TransferFailed();

        emit SinglePaymentSent(msg.sender, recipient, amount);
    }

    /**
     * @notice Batch send ETH to multiple recipients.
     * @param recipients Array of addresses to receive ETH.
     * @param amounts Array of amounts in wei (parallel array to recipients).
     * @dev Uses assembly for gas-efficient loops.
     */
    function batchSendETH(
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external payable {
        if (recipients.length != amounts.length) revert InvalidPaymentAmount();

        uint256 totalAmount;
        unchecked {
            for (uint256 i = 0; i < recipients.length; i++) {
                totalAmount += amounts[i];
            }
        }
        if (msg.value != totalAmount) revert InvalidPaymentAmount();

        // Gas-efficient loop with assembly
        bool allSuccess = true;
        assembly {
            let len := recipients.length
            let i := 0
            for { } lt(i, len) { } {
                let recipient := calldataload(add(recipients.offset, mul(i, 0x20)))
                let amount := calldataload(add(amounts.offset, mul(i, 0x20)))
                
                let success := call(gas(), recipient, amount, 0, 0, 0, 0)
                if iszero(success) {
                    allSuccess := false
                    break
                }
                i := add(i, 1)
            }
        }
        if (!allSuccess) revert TransferFailed();

        emit BatchPaymentSent(msg.sender, totalAmount, recipients.length);
    }

    // ------------------------ ERC20 Support ------------------------
    /**
     * @notice Batch send ERC20 tokens (requires prior approval).
     * @param token ERC20 token contract address.
     * @param recipients Array of recipient addresses.
     * @param amounts Array of token amounts.
     */
    function batchSendERC20(
        address token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        if (recipients.length != amounts.length) revert InvalidPaymentAmount();

        bool allSuccess = true;
        for (uint256 i = 0; i < recipients.length; ) {
            (bool success, ) = token.call(
                abi.encodeWithSelector(
                    0xa9059cbb, // transfer(address,uint256)
                    recipients[i],
                    amounts[i]
                )
            );
            if (!success) {
                allSuccess = false;
                break;
            }
            unchecked { i++; }
        }
        if (!allSuccess) revert TransferFailed();
    }
}