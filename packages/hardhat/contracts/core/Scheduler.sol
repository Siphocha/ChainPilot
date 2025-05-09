// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ChainPilot - Scheduler Contract
 * @notice Queues time-based tasks for off-chain keepers to execute via Executer.
 * @dev Features tight integration with Executer contract, packed storage, and enhanced security.
 */

import { ChainPilotExecutor } from "./Executor.sol";

contract ChainPilotScheduler is ChainPilotExecutor {

    // ------------------------ Custom Errors ------------------------
    error Unauthorized(address caller, address owner);
    error InvalidTask(string reason);
    error TaskNotFound(uint256 taskId);
    error TaskAlreadyCancelled(uint256 taskId);
    error InvalidTimeWindow(uint256 from, uint256 to);
    error ExecutionWindowNotReached(uint256 executeAt, uint256 currentTime);
    error ExecutionWindowExpired(uint256 executeAt, uint256 expiry);

    // ------------------------ Events ------------------------
    event TaskScheduled(
        uint256 indexed taskId,
        address indexed user,
        address indexed executer,
        address target,
        uint64 executeAt,
        uint64 expiryAt,
        bytes32 payloadHash,
        uint256 value
    );
    event TaskCancelled(uint256 indexed taskId);
    event TaskExecuted(uint256 indexed taskId, address indexed executor);

    // ------------------------ Structs ------------------------
    struct Task {
        uint64 executeAt;       
        uint64 expiryAt;        
        address user;          
        address executer;      
        address target;         
        bytes32 payloadHash;    
        uint256 value;         
        bool isCancelled;      
    }

    // ------------------------ Storage ------------------------
    mapping(uint256 => Task) public tasks;
    uint256 public taskIdCounter;
    address public immutable executerAddress;

    // ------------------------ Constructor ------------------------
    constructor(address _executer) {
        executerAddress = _executer;
    }

    // ------------------------ Modifiers ------------------------
    modifier onlyTaskOwner(uint256 taskId) {
        if (tasks[taskId].user != msg.sender) {
            revert Unauthorized(msg.sender, tasks[taskId].user);
        }
        _;
    }

    modifier validTask(uint256 taskId) {
        if (taskId >= taskIdCounter) revert TaskNotFound(taskId);
        _;
    }

    // ------------------------ External Functions ------------------------
    /**
     * @notice Schedule a new task via Executer
     * @param executeAt When the task should run (timestamp)
     * @param expiryAt When the task becomes invalid (0 for no expiry)
     * @param target The final target contract
     * @param payload Encoded function call data
     * @param value ETH/value to be sent with the call
     */
    function scheduleTask(
        uint64 executeAt,
        uint64 expiryAt,
        address target,
        bytes calldata payload,
        uint256 value
    ) external returns (uint256 taskId) {
        if (executeAt < block.timestamp + 60) {
            revert InvalidTask("Execution time must be at least 1 minute in future");
        }
        if (expiryAt != 0 && expiryAt <= executeAt) {
            revert InvalidTask("Expiry must be after execution time");
        }
        if (target == address(0)) {
            revert InvalidTask("Target cannot be zero address");
        }

        taskId = taskIdCounter++;
        bytes32 payloadHash = keccak256(payload);
        
        tasks[taskId] = Task({
            executeAt: executeAt,
            expiryAt: expiryAt,
            user: msg.sender,
            executer: executerAddress,
            target: target,
            payloadHash: payloadHash,
            value: value,
            isCancelled: false
        });

        emit TaskScheduled(
            taskId,
            msg.sender,
            executerAddress,
            target,
            executeAt,
            expiryAt,
            payloadHash,
            value
        );
    }

    /**
     * @notice Cancel a scheduled task
     */
    function cancelTask(uint256 taskId) 
        external 
        validTask(taskId)
        onlyTaskOwner(taskId)
    {
        Task storage task = tasks[taskId];
        
        if (task.isCancelled) revert TaskAlreadyCancelled(taskId);
        if (block.timestamp >= task.executeAt) {
            revert ExecutionWindowNotReached(task.executeAt, block.timestamp);
        }

        task.isCancelled = true;
        emit TaskCancelled(taskId);
    }

    // ------------------------ Keeper Functions ------------------------
    /**
     * @notice Execute a scheduled task via Executer
     */
    function executeTask(uint256 taskId) 
        external 
        validTask(taskId)
        returns (bool)
    {
        Task memory task = tasks[taskId];

        if (task.isCancelled) revert TaskAlreadyCancelled(taskId);
        if (block.timestamp < task.executeAt) {
            revert ExecutionWindowNotReached(task.executeAt, block.timestamp);
        }
        if (task.expiryAt != 0 && block.timestamp > task.expiryAt) {
            revert ExecutionWindowExpired(task.executeAt, task.expiryAt);
        }

        // prevent re-execution
        tasks[taskId].isCancelled = true;

        // Forward to Executer contract
        bool success = ChainPilotExecutor(task.executer).executeTask{value: task.value}(
            task.user,
            task.target,
            task.payloadHash,
            task.value
        );

        emit TaskExecuted(taskId, msg.sender);
        return success;
    }

    // ------------------------ View Functions ------------------------
    /**
     * @notice Get pending tasks within a time range
     */
    function getPendingTasks(uint256 from, uint256 to) 
        external 
        view 
        returns (uint256[] memory) 
    {
        if (from > to) revert InvalidTimeWindow(from, to);
        
        uint256[] memory pendingTasks = new uint256[](taskIdCounter);
        uint256 count = 0;

        for (uint256 i = 0; i < taskIdCounter; i++) {
            Task memory task = tasks[i];
            if (!task.isCancelled && 
                task.executeAt >= from && 
                task.executeAt <= to &&
                (task.expiryAt == 0 || block.timestamp <= task.expiryAt)) {
                pendingTasks[count++] = i;
            }
        }

        assembly { mstore(pendingTasks, count) }
        return pendingTasks;
    }
}