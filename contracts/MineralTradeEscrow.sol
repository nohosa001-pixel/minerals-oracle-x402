// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev Minimal ERC-20 interface (USDC / EURC).
 */
interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title MineralTradeEscrow
 * @author Minerals Oracle Team
 * @notice Milestone-based autonomous AI escrow contract for critical minerals and battery materials.
 *         Releases funds in 3 stages:
 *         1. Stage 1 (30%): Electronic Bill of Lading (eBL) anchored & verified by Oracle.
 *         2. Stage 2 (40%): Mid-transit corridor verification (AIS / Satellite tracking).
 *         3. Stage 3 (30%): Port of Discharge customs clearance & battery passport verification.
 */
contract MineralTradeEscrow {
    enum EscrowStatus {
        CREATED,
        STAGE_1_BL_RELEASED,
        STAGE_2_TRANSIT_RELEASED,
        COMPLETED,
        REFUNDED,
        DISPUTED
    }

    struct TradeDeal {
        bytes32 dealId;
        address buyerAgent;
        address sellerAgent;
        uint256 totalAmountUsdc;
        uint256 releasedAmountUsdc;
        bytes32 eblHash;
        uint256 deadlineTimestamp;
        EscrowStatus status;
    }

    address public owner;
    address public trustedOracleSigner;
    IERC20 public immutable usdcToken;

    mapping(bytes32 => TradeDeal) public deals;

    event EscrowCreated(bytes32 indexed dealId, address indexed buyer, address indexed seller, uint256 totalAmount, bytes32 eblHash);
    event Stage1Released(bytes32 indexed dealId, uint256 amountReleased, bytes32 eblDigest);
    event Stage2Released(bytes32 indexed dealId, uint256 amountReleased);
    event EscrowCompleted(bytes32 indexed dealId, uint256 finalAmountReleased);
    event EscrowRefunded(bytes32 indexed dealId, uint256 refundedAmount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner permitted");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == trustedOracleSigner || msg.sender == owner, "Only trusted oracle permitted");
        _;
    }

    constructor(address _usdcToken, address _trustedOracleSigner) {
        require(_usdcToken != address(0), "Invalid token address");
        require(_trustedOracleSigner != address(0), "Invalid oracle address");
        owner = msg.sender;
        usdcToken = IERC20(_usdcToken);
        trustedOracleSigner = _trustedOracleSigner;
    }

    /**
     * @notice Buyer agent creates and funds escrow for an agreed bilateral trade deal.
     */
    function createEscrow(
        bytes32 dealId,
        address sellerAgent,
        uint256 amountUsdc,
        bytes32 eblHash,
        uint256 durationSeconds
    ) external {
        require(deals[dealId].buyerAgent == address(0), "Deal already exists");
        require(sellerAgent != address(0) && sellerAgent != msg.sender, "Invalid seller address");
        require(amountUsdc > 0, "Amount must be > 0");
        require(durationSeconds >= 60, "Duration must be at least 60 seconds");

        bool ok = usdcToken.transferFrom(msg.sender, address(this), amountUsdc);
        require(ok, "USDC deposit failed");

        deals[dealId] = TradeDeal({
            dealId: dealId,
            buyerAgent: msg.sender,
            sellerAgent: sellerAgent,
            totalAmountUsdc: amountUsdc,
            releasedAmountUsdc: 0,
            eblHash: eblHash,
            deadlineTimestamp: block.timestamp + durationSeconds,
            status: EscrowStatus.CREATED
        });

        emit EscrowCreated(dealId, msg.sender, sellerAgent, amountUsdc, eblHash);
    }

    /**
     * @notice Stage 1: Oracle verifies eBL loading manifest on-chain and releases 30% to seller.
     */
    function releaseStage1BL(bytes32 dealId, bytes32 verifiedEblHash) external onlyOracle {
        TradeDeal storage deal = deals[dealId];
        require(deal.status == EscrowStatus.CREATED, "Invalid stage transition");
        require(deal.eblHash == verifiedEblHash, "eBL hash mismatch");

        uint256 stage1Amount = (deal.totalAmountUsdc * 30) / 100;
        deal.releasedAmountUsdc += stage1Amount;
        deal.status = EscrowStatus.STAGE_1_BL_RELEASED;

        bool ok = usdcToken.transfer(deal.sellerAgent, stage1Amount);
        require(ok, "Stage 1 transfer failed");

        emit Stage1Released(dealId, stage1Amount, verifiedEblHash);
    }

    /**
     * @notice Stage 2: Mid-transit corridor verification (40% release to seller).
     */
    function releaseStage2Transit(bytes32 dealId) external onlyOracle {
        TradeDeal storage deal = deals[dealId];
        require(deal.status == EscrowStatus.STAGE_1_BL_RELEASED, "Must release Stage 1 first");

        uint256 stage2Amount = (deal.totalAmountUsdc * 40) / 100;
        deal.releasedAmountUsdc += stage2Amount;
        deal.status = EscrowStatus.STAGE_2_TRANSIT_RELEASED;

        bool ok = usdcToken.transfer(deal.sellerAgent, stage2Amount);
        require(ok, "Stage 2 transfer failed");

        emit Stage2Released(dealId, stage2Amount);
    }

    /**
     * @notice Stage 3: Port of discharge arrival, customs clearance & passport minting (Final 30%).
     */
    function completeEscrow(bytes32 dealId) external onlyOracle {
        TradeDeal storage deal = deals[dealId];
        require(deal.status == EscrowStatus.STAGE_2_TRANSIT_RELEASED, "Must complete Stage 2 first");

        uint256 remainingAmount = deal.totalAmountUsdc - deal.releasedAmountUsdc;
        deal.releasedAmountUsdc += remainingAmount;
        deal.status = EscrowStatus.COMPLETED;

        bool ok = usdcToken.transfer(deal.sellerAgent, remainingAmount);
        require(ok, "Final transfer failed");

        emit EscrowCompleted(dealId, remainingAmount);
    }

    /**
     * @notice Refund remaining unreleased funds back to buyer if contract expires without completion.
     */
    function refundExpiredDeal(bytes32 dealId) external {
        TradeDeal storage deal = deals[dealId];
        require(
            deal.status != EscrowStatus.COMPLETED && deal.status != EscrowStatus.REFUNDED,
            "Already settled or refunded"
        );
        require(block.timestamp > deal.deadlineTimestamp, "Deal has not expired");
        require(msg.sender == deal.buyerAgent || msg.sender == owner, "Only buyer or owner can refund");

        uint256 remaining = deal.totalAmountUsdc - deal.releasedAmountUsdc;
        require(remaining > 0, "No remaining balance");

        deal.status = EscrowStatus.REFUNDED;
        bool ok = usdcToken.transfer(deal.buyerAgent, remaining);
        require(ok, "Refund transfer failed");

        emit EscrowRefunded(dealId, remaining);
    }

    /**
     * @notice Returns trade deal information.
     */
    function getDeal(bytes32 dealId) external view returns (TradeDeal memory) {
        return deals[dealId];
    }
}
