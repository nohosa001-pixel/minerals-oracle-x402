// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev Minimal interface for standard ERC-20 token (USDC on Polygon).
 */
interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentPaymentVault
 * @author Minerals Oracle Team (Polygon Network)
 * @notice Pre-funded payment vault for autonomous AI agents consuming Minerals Oracle feeds.
 *         Allows AI agents to deposit USDC in advance, enabling sub-millisecond zero-latency
 *         off-chain balance deductions by the oracle facilitator.
 */
contract AgentPaymentVault {
    address public owner;
    address public oracleOperator;
    IERC20 public immutable usdcToken;

    // Agent balance tracking (in 6 decimals USDC, e.g. $10.00 = 10_000_000)
    mapping(address => uint256) public agentBalances;
    mapping(address => uint256) public totalDeposited;
    mapping(address => uint256) public totalConsumed;

    event AgentDeposited(address indexed agent, uint256 amountUsdc, uint256 newBalance);
    event AgentWithdrawn(address indexed agent, uint256 amountUsdc, uint256 remainingBalance);
    event BatchSettled(uint256 totalUsdcSettled, uint256 agentCount, bytes32 batchDigest);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner permitted");
        _;
    }

    modifier onlyOperator() {
        require(msg.sender == oracleOperator || msg.sender == owner, "Only operator permitted");
        _;
    }

    constructor(address _usdcTokenAddress, address _oracleOperator) {
        require(_usdcTokenAddress != address(0), "Invalid USDC address");
        require(_oracleOperator != address(0), "Invalid operator address");
        owner = msg.sender;
        usdcToken = IERC20(_usdcTokenAddress);
        oracleOperator = _oracleOperator;
    }

    /**
     * @notice Allows an AI agent to deposit USDC into their pre-funded vault balance.
     * @param amountUsdc Amount of USDC (6 decimals) to deposit.
     */
    function deposit(uint256 amountUsdc) external {
        require(amountUsdc > 0, "Deposit amount must be > 0");
        bool success = usdcToken.transferFrom(msg.sender, address(this), amountUsdc);
        require(success, "USDC transfer failed");

        agentBalances[msg.sender] += amountUsdc;
        totalDeposited[msg.sender] += amountUsdc;

        emit AgentDeposited(msg.sender, amountUsdc, agentBalances[msg.sender]);
    }

    /**
     * @notice Allows an AI agent to withdraw unused balance back to their wallet.
     * @param amountUsdc Amount to withdraw.
     */
    function withdraw(uint256 amountUsdc) external {
        require(amountUsdc > 0, "Withdraw amount must be > 0");
        require(agentBalances[msg.sender] >= amountUsdc, "Insufficient vault balance");

        agentBalances[msg.sender] -= amountUsdc;
        bool success = usdcToken.transfer(msg.sender, amountUsdc);
        require(success, "USDC withdrawal transfer failed");

        emit AgentWithdrawn(msg.sender, amountUsdc, agentBalances[msg.sender]);
    }

    /**
     * @notice Oracle operator settles aggregated consumption batches and sweeps earned oracle fees.
     * @param agents Array of agent addresses to deduct from.
     * @param amounts Array of consumed USDC amounts.
     * @param treasury Destination treasury wallet for oracle earnings.
     * @param batchDigest Cryptographic audit hash of the off-chain consumption logs.
     */
    function settleConsumptionBatch(
        address[] calldata agents,
        uint256[] calldata amounts,
        address treasury,
        bytes32 batchDigest
    ) external onlyOperator {
        require(agents.length == amounts.length, "Arrays length mismatch");
        require(treasury != address(0), "Invalid treasury address");

        uint256 totalSettled = 0;
        for (uint256 i = 0; i < agents.length; i++) {
            address agent = agents[i];
            uint256 amount = amounts[i];
            if (agentBalances[agent] >= amount) {
                agentBalances[agent] -= amount;
                totalConsumed[agent] += amount;
                totalSettled += amount;
            }
        }

        if (totalSettled > 0) {
            bool success = usdcToken.transfer(treasury, totalSettled);
            require(success, "Treasury transfer failed");
        }

        emit BatchSettled(totalSettled, agents.length, batchDigest);
    }

    /**
     * @notice Returns current available balance for an agent in USDC units (e.g. 10.50 USDC -> 10500000).
     */
    function getBalance(address agent) external view returns (uint256) {
        return agentBalances[agent];
    }
}
