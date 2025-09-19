// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./StakingBase.sol";

/**
 * @title StakingToken
 * @dev ERC20 token staking implementation inheriting from StakingBase
 * 
 * This contract handles OLAS token deposits and withdrawals for staking services.
 * It implements the abstract functions from StakingBase to work with ERC20 tokens.
 */
contract StakingToken is StakingBase {
    /// @dev Token contract address
    address public immutable stakingToken;

    /// @dev Events
    event TokenDeposit(address indexed sender, uint256 amount);
    event TokenWithdraw(address indexed recipient, uint256 amount);

    /// @dev Errors
    error TransferFailed();

    /**
     * @dev Constructor for StakingToken
     * @param _stakingToken Address of the ERC20 token to be staked (OLAS)
     * @param _stakingParams Struct containing all staking parameters
     */
    constructor(
        address _stakingToken,
        StakingParams memory _stakingParams
    ) StakingBase(_stakingParams) {
        if (_stakingToken == address(0)) revert ZeroAddress();
        stakingToken = _stakingToken;
    }

    /**
     * @dev Handle token deposit from user during staking
     * @param from Address to transfer tokens from
     * @param amount Amount of tokens to deposit
     */
    function _deposit(address from, uint256 amount) internal override {
        bool success = IERC20(stakingToken).transferFrom(from, address(this), amount);
        if (!success) revert TransferFailed();
        
        emit TokenDeposit(from, amount);
    }

    /**
     * @dev Handle token withdrawal to user during unstaking
     * @param to Address to send tokens to
     * @param amount Amount of tokens to withdraw
     */
    function _withdraw(address to, uint256 amount) internal override {
        bool success = IERC20(stakingToken).transfer(to, amount);
        if (!success) revert TransferFailed();
        
        emit TokenWithdraw(to, amount);
    }

    /**
     * @dev Get the balance of staking tokens held by this contract
     * @return Token balance
     */
    function getTokenBalance() external view returns (uint256) {
        return IERC20(stakingToken).balanceOf(address(this));
    }

    /**
     * @dev Emergency function to recover tokens (only for testing)
     * In production, this should have proper access control
     * @param to Address to send tokens to
     * @param amount Amount to recover
     */
    function recoverTokens(address to, uint256 amount) external {
        // In production, add proper access control here
        // require(msg.sender == owner, "Only owner");
        
        bool success = IERC20(stakingToken).transfer(to, amount);
        if (!success) revert TransferFailed();
        
        emit TokenWithdraw(to, amount);
    }
}
