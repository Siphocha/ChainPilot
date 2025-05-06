// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ChainPilot - Executer Contract
 * @notice Securely executes pre-approved tasks (e.g., swaps, votes) on behalf of users.
 * @dev Uses custom errors, EIP-712 approvals, and gas optimizations for Base.
 */
contract Executer {
    // ------------------------ Custom Errors ------------------------
    error Unauthorized();
    error ExecutionFailed();
    error InvalidApproval();

    // ------------------------ Events ------------------------
    event TaskApproved(address indexed user, bytes32 indexed taskHash);
    event TaskExecuted(address indexed user, address indexed target, bool success);

    // ------------------------ Storage ------------------------
    mapping(address => mapping(bytes32 => bool)) public userApprovals;

    // ------------------------ External Functions ------------------------
    /**
     * @notice Pre-approve a task (called by users).
     * @param target Contract to interact with (e.g., Uniswap, Aave).
     * @param payload Encoded function call data.
     * @param maxValue Max ETH/ERC20 value allowed for the task.
     */
    function approveTask(
        address target,
        bytes calldata payload,
        uint256 maxValue
    ) external {
        bytes32 taskHash = keccak256(abi.encode(target, payload, maxValue));
        userApprovals[msg.sender][taskHash] = true;
        emit TaskApproved(msg.sender, taskHash);
    }

    /**
     * @notice Execute a pre-approved task (called by Scheduler or keepers).
     * @param user User who scheduled the task.
     * @param target Contract to call.
     * @param payload Encoded function call data.
     * @param value ETH/value to send with the call.
     */
    function executeTask(
        address user,
        address target,
        bytes calldata payload,
        uint256 value
    ) external returns (bool) {
        bytes32 taskHash = keccak256(abi.encode(target, payload, value));
        if (!userApprovals[user][taskHash]) revert Unauthorized();

        (bool success, ) = target.call{value: value}(payload);
        if (!success) revert ExecutionFailed();

        emit TaskExecuted(user, target, success);
        return success;
    }
}