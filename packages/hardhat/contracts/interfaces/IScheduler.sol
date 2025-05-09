// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IScheduler {
    function scheduleTask(uint256 executeAt, address target, bytes calldata payload) external;
    function cancelTask(uint256 taskId) external;
}
