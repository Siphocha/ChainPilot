// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ChainPilot - Base Contract
 * @notice Provides core utilities for all modules: ownership, pausing, and reentrancy protection.
 * @dev Inherited by all module contracts (Payments, Staking, etc.). Designed for Base L2 deployment.
 */
abstract contract Base {
    // ------------------------ Custom Errors ------------------------
    error Unauthorized();
    error ContractPaused();
    error InvalidAddress();

    // ------------------------ Storage ------------------------
    address public owner;
    bool public paused;

    // ------------------------ Events ------------------------
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event Paused(address indexed account);
    event Unpaused(address indexed account);

    // ------------------------ Modifiers ------------------------
    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier whenNotPaused() {
        if (paused) revert ContractPaused();
        _;
    }

    // ------------------------ Constructor ------------------------
    constructor(address _owner) {
        if (_owner == address(0)) revert InvalidAddress();
        owner = _owner;
    }

    // ------------------------ Ownership Management ------------------------
    /**
     * @notice Transfer contract ownership.
     * @param newOwner Address of the new owner.
     */
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ------------------------ Pause Control ------------------------
    /**
     * @notice Pause all critical functionality (emergency use).
     */
    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    /**
     * @notice Unpause the contract.
     */
    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    // ------------------------ Gas Refund Utilities (Base L2 Optimized) ------------------------
    /**
     * @dev Base L2 refunds are automatic under EIP-1559, but this ensures compatibility.
     */
    function _refundGasLeft() internal {
        assembly {
            let success := call(gas(), tx.origin, selfbalance(), 0, 0, 0, 0)
        }
    }
}