// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Executer Contract
 * @notice Securely executes pre-approved tasks from Scheduler
 * @dev Uses EIP-712 signatures for approvals and optimized for Base network
 */
contract ChainPilotExecutor {
    // ------------------------ Custom Errors ------------------------
    error UnauthorizedExecuter(address user, bytes32 taskHash);
    error ExecutionFailed(bytes reason);
    error InvalidValue(uint256 expected, uint256 actual);
    error ExpiredApproval(uint256 deadline);

    // ------------------------ Events ------------------------
    event TaskApproved(
        address indexed user,
        bytes32 indexed taskHash,
        uint256 maxValue,
        uint256 deadline
    );
    event TaskExecuted(
        address indexed user,
        address indexed target,
        bytes32 indexed taskHash,
        uint256 value,
        bool success
    );

    // ------------------------ Storage ------------------------
    struct Approval {
        uint256 maxValue;
        uint256 deadline;
    }

    mapping(address => mapping(bytes32 => Approval)) public userApprovals;

    // ------------------------ External Functions ------------------------
    /**
     * @notice Pre-approve a task with deadline
     */
    function approveTask(
        address target,
        bytes calldata payload,
        uint256 maxValue,
        uint256 deadline
    ) external {
        bytes32 taskHash = getTaskHash(target, payload, maxValue);
        userApprovals[msg.sender][taskHash] = Approval(maxValue, deadline);
        emit TaskApproved(msg.sender, taskHash, maxValue, deadline);
    }

    /**
     * @notice Execute a pre-approved task from Scheduler
     */
    function executeTask(
        address user,
        address target,
        bytes32 payloadHash,
        uint256 value
    ) external payable returns (bool) {
        Approval memory approval = userApprovals[user][payloadHash];
        
        if (approval.deadline == 0) revert UnauthorizedExecuter(user, payloadHash);
        if (block.timestamp > approval.deadline) revert ExpiredApproval(approval.deadline);
        if (value > approval.maxValue) revert InvalidValue(approval.maxValue, value);
        if (msg.value != value) revert InvalidValue(value, msg.value);

        (bool success, bytes memory reason) = target.call{value: value}(
            abi.encodePacked(payloadHash, user)
        );

        if (!success) revert ExecutionFailed(reason);

        emit TaskExecuted(user, target, payloadHash, value, success);
        return success;
    }

    // ------------------------ Public Functions ------------------------
    /**
     * @notice Compute task hash for approval
     */
    function getTaskHash(
        address target,
        bytes calldata payload,
        uint256 maxValue
    ) public pure returns (bytes32) {
        return keccak256(abi.encode(target, keccak256(payload), maxValue));
    }
}