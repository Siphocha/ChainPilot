// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IExecutor {
    function executeTask(uint256 taskId) external;
}