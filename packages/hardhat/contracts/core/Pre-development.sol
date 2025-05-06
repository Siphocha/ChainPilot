// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ChainPilot - Scheduler Contract
 * @notice Queues time-based tasks for offchain keepers to execute.
 * @dev Uses custom errors, minimal storage, and event-driven architecture.
 */
contract Scheduler {
    // ------------------------ Custom Errors ------------------------
    error Unauthorized();
    error InvalidTask();
    error TaskAlreadyCancelled();

    // ------------------------ Structs & Events ------------------------
    struct Task {
        uint256 executeAt;
        address user;
        address target;
        bytes payload;
        bool isCancelled;
    }

    event TaskScheduled(uint256 indexed taskId, address indexed user, uint256 executeAt);
    event TaskCancelled(uint256 indexed taskId);

    // ------------------------ Storage ------------------------
    mapping(uint256 => Task) public tasks;
    uint256 public taskIdCounter;

    // ------------------------ External Functions ------------------------
    /**
     * @notice Schedule a new task.
     * @param executeAt When the task should run (timestamp).
     * @param target The contract to call (e.g., Executer.sol).
     * @param payload Encoded function call data.
     */
    function scheduleTask(
        uint256 executeAt,
        address target,
        bytes calldata payload
    ) external returns (uint256 taskId) {
        if (executeAt < block.timestamp || target == address(0)) revert InvalidTask();

        taskId = taskIdCounter++;
        tasks[taskId] = Task(executeAt, msg.sender, target, payload, false);

        emit TaskScheduled(taskId, msg.sender, executeAt);
    }

    /**
     * @notice Cancel a scheduled task.
     * @param taskId ID of the task to cancel.
     */
    function cancelTask(uint256 taskId) external {
        Task storage task = tasks[taskId];
        if (task.user != msg.sender) revert Unauthorized();
        if (task.isCancelled) revert TaskAlreadyCancelled();

        task.isCancelled = true;
        emit TaskCancelled(taskId);
    }

    // ------------------------ View Functions (For Keepers) ------------------------
    /**
     * @notice Get pending task IDs within a range.
     * @dev Offchain keepers (Gelato) call this to find executable tasks.
     */
    function getPendingTasks(uint256 from, uint256 to) external view returns (uint256[] memory) {
        uint256[] memory pendingTasks = new uint256[](to - from + 1);
        uint256 count = 0;

        for (uint256 i = from; i <= to; i++) {
            Task memory task = tasks[i];
            if (block.timestamp >= task.executeAt && !task.isCancelled) {
                pendingTasks[count++] = i;
            }
        }

        // Resize array to fit actual results (saves gas for keeper)
        assembly { mstore(pendingTasks, count) }
        return pendingTasks;
    }
}