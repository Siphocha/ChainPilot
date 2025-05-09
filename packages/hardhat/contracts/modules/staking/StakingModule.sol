// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Base} from "../base/Base.sol";

/**
 * @title ChainPilot - Staking Module
 * @notice Handles ERC20/ETH staking with time/amount-based rewards.
 * @dev Inherits from Base.sol for ownership/pausing. Uses checkpointing for scalable rewards.
 */
contract StakingModule is Base {
    // ------------------------ Structs & Events ------------------------
    struct Stake {
        uint256 amount;
        uint256 startTime;
        uint256 lastClaimTime;
    }

    struct RewardConfig {
        uint256 rate; // Rewards per second per token (wei)
        uint256 minStakeDuration;
        address rewardToken;
    }

    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 amount);

    error InvalidAmount();
    error NoStake();

    // ------------------------ Storage ------------------------
    IERC20 public immutable stakingToken;
    RewardConfig public rewardConfig;

    mapping(address => Stake) public stakes;
    uint256 public totalStaked;

    // ------------------------ Constructor ------------------------
    constructor(
        address _owner,
        address _stakingToken,
        uint256 _rewardRate,
        uint256 _minStakeDuration,
        address _rewardToken
    ) Base(_owner) {
        stakingToken = IERC20(_stakingToken);
        rewardConfig = RewardConfig(
            _rewardRate,
            _minStakeDuration,
            _rewardToken
        );
    }

    // ------------------------ External Functions ------------------------
    /**
     * @notice Stake tokens to earn rewards.
     * @param amount Amount of tokens to stake (must approve first).
     */
    function stake(uint256 amount) external whenNotPaused {
        if (amount == 0) revert InvalidAmount();

        Stake storage userStake = stakes[msg.sender];
        _claimRewards(msg.sender); // Claim pending rewards first

        userStake.amount += amount;
        userStake.startTime = block.timestamp;
        userStake.lastClaimTime = block.timestamp;

        totalStaked += amount;
        stakingToken.transferFrom(msg.sender, address(this), amount);

        emit Staked(msg.sender, amount);
    }

    /**
     * @notice Unstake tokens (forfeits unclaimed rewards if early).
     */
    function unstake() external {
        Stake memory userStake = stakes[msg.sender];
        if (userStake.amount == 0) revert NoStake();

        uint256 amount = userStake.amount;
        totalStaked -= amount;

        // Penalize early unstakes
        if (block.timestamp < userStake.startTime + rewardConfig.minStakeDuration) {
            amount = (amount * 80) / 100; // 20% penalty
        } else {
            _claimRewards(msg.sender);
        }

        delete stakes[msg.sender];
        stakingToken.transfer(msg.sender, amount);

        emit Unstaked(msg.sender, amount);
    }

    /**
     * @notice Claim pending rewards without unstaking.
     */
    function claimRewards() external {
        _claimRewards(msg.sender);
    }

    // ------------------------ View Functions ------------------------
    /**
     * @notice Calculate pending rewards for a user.
     * @dev Uses checkpointing to avoid storage writes during reads.
     */
    function pendingRewards(address user) public view returns (uint256) {
        Stake memory userStake = stakes[user];
        if (userStake.amount == 0) return 0;

        uint256 elapsed = block.timestamp - userStake.lastClaimTime;
        return (userStake.amount * rewardConfig.rate * elapsed) / 1e18;
    }

    // ------------------------ Admin Functions ------------------------
    /**
     * @notice Update reward rate (owner only).
     */
    function setRewardRate(uint256 newRate) external onlyOwner {
        rewardConfig.rate = newRate;
    }

    // ------------------------ Internal Functions ------------------------
    function _claimRewards(address user) internal {
        uint256 rewards = pendingRewards(user);
        if (rewards == 0) return;

        stakes[user].lastClaimTime = block.timestamp;
        IERC20(rewardConfig.rewardToken).transfer(user, rewards);

        emit RewardClaimed(user, rewards);
    }
}