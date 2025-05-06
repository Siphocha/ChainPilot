// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ChainPilot - Automation Agent
 * @notice Orchestrates tasks, handles gas, and integrates offchain agents/AI.
 * @dev Acts as a middleware between users and core contracts (Scheduler/Executer).
 */
contract AutomationAgent {
    // ------------------------ Custom Errors ------------------------
    error Unauthorized();
    error InsufficientGasCredit();
    error TaskConditionsNotMet();

    // ------------------------ Structs & Events ------------------------
    struct TaskConfig {
        address user;
        address target;
        bytes payload;
        uint256 gasCredit;  // Prepaid gas budget (optional)
        bytes32 conditionsHash;  // E.g., "APY > 5%" (checked offchain)
    }

    event TaskSubscribed(uint256 indexed taskId, address indexed user);
    event TaskAutoExecuted(uint256 indexed taskId, bool success);

    // ------------------------ Immutables ------------------------
    address public immutable scheduler;
    address public immutable executer;

    // ------------------------ Storage ------------------------
    mapping(uint256 => TaskConfig) public tasks;
    uint256 public taskIdCounter;

    // ------------------------ Constructor ------------------------
    constructor(address _scheduler, address _executer) {
        scheduler = _scheduler;
        executer = _executer;
    }

    // ------------------------ Core Functions ------------------------
    /**
     * @notice Subscribe to a new automated task (called by users).
     * @param target Contract to interact with (e.g., Executer.sol).
     * @param payload Encoded function call.
     * @param gasCredit ETH reserved for gas (use 0 for self-funded).
     * @param conditionsHash Offchain-checked conditions (e.g., "APY > 5%").
     */
    function subscribeTask(
        address target,
        bytes calldata payload,
        uint256 gasCredit,
        bytes32 conditionsHash
    ) external payable returns (uint256 taskId) {
        taskId = taskIdCounter++;
        tasks[taskId] = TaskConfig(
            msg.sender,
            target,
            payload,
            gasCredit,
            conditionsHash
        );

        if (gasCredit > 0) {
            // User prepays gas (optional)
            if (msg.value < gasCredit) revert InsufficientGasCredit();
        }

        emit TaskSubscribed(taskId, msg.sender);
    }

    /**
     * @notice Execute a task if conditions are met (called by offchain AI/keeper).
     * @dev Offchain agents validate conditionsHash before calling.
     */
    function executeTask(
        uint256 taskId,
        bytes calldata conditionsProof  // E.g., signed APY data
    ) external {
        TaskConfig memory config = tasks[taskId];
        if (config.user == address(0)) revert Unauthorized();

        // Validate conditions (offchain proof or onchain checks)
        if (!_validateConditions(config.conditionsHash, conditionsProof)) {
            revert TaskConditionsNotMet();
        }

        // Use prepaid gas or user's wallet
        uint256 gasToUse = config.gasCredit > 0 ? config.gasCredit : 0;

        (bool success, ) = executer.call{value: gasToUse}(
            abi.encodeWithSignature(
                "executeTask(address,address,bytes,uint256)",
                config.user,
                config.target,
                config.payload,
                0  // value (ETH) can be embedded in payload)
            )
        );

        emit TaskAutoExecuted(taskId, success);
    }

    // ------------------------ Internal ------------------------
    function _validateConditions(
        bytes32 conditionsHash,
        bytes calldata proof
    ) internal pure returns (bool) {
        // Example: Verify signed offchain data (e.g., APY > 5%)
        // For MVP, assume proof is valid (add Chainlink/Oracle later)
        return conditionsHash == keccak256(proof);
    }
}