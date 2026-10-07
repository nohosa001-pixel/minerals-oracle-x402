// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev Minimal ERC-20 Interface (USDC / EURC).
 */
interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @dev Minimal Pyth Price Feed Interface.
 */
interface IPyth {
    struct Price {
        int64 price;
        uint64 conf;
        int32 expo;
        uint256 publishTime;
    }
    function getPriceUnsafe(bytes32 id) external view returns (Price memory price);
}

/**
 * @title DynamicTradeEscrow
 * @author A.GRID / Minerals Oracle Team
 * @notice Enterprise dynamic escrow contract with Pyth Network real-time mark-to-market valuation,
 *         tripartite multi-party release (Oracle Proof + Carrier B/L Arrival + Inspector Purity),
 *         and autonomous margin-call defense for high-value mineral commodities.
 */
contract DynamicTradeEscrow {
    enum EscrowStatus {
        ACTIVE,
        CUSTOMS_CLEARED,
        RELEASED_SETTLED,
        MARGIN_CALLED,
        REFUNDED,
        DISPUTED
    }

    struct DynamicDeal {
        bytes32 dealId;
        address buyerAgent;
        address sellerAgent;
        address inspector;
        uint256 totalAmountUsdc;
        uint256 collateralDepositUsdc;
        bytes32 pythPriceId;
        int64 basePriceUsd;              // Price at deal initiation (8 decimals)
        uint256 minCollateralRatioBps;   // Basis points e.g. 11000 = 110%
        bytes32 oracleProofHash;
        bool oracleProofVerified;
        bool carrierArrivalConfirmed;
        bool inspectorPurityPassed;
        uint256 expiryTimestamp;
        EscrowStatus status;
    }

    address public owner;
    address public trustedOracleSigner;
    IPyth public pythOracle;
    IERC20 public immutable usdcToken;
    bool public paused;

    uint256 private _reentrancyStatus;
    mapping(bytes32 => DynamicDeal) public deals;

    event DynamicDealCreated(bytes32 indexed dealId, address indexed buyer, address indexed seller, uint256 amountUsdc, bytes32 pythPriceId);
    event OracleProofAnchored(bytes32 indexed dealId, bytes32 proofHash);
    event CarrierArrivalNotified(bytes32 indexed dealId);
    event InspectorAttested(bytes32 indexed dealId, bool passed);
    event CustomsCleared(bytes32 indexed dealId);
    event DealSettled(bytes32 indexed dealId, uint256 grossPayout);
    event MarginCallTriggered(bytes32 indexed dealId, int64 currentPrice, uint256 requiredTopupUsdc);
    event MarginTopupDeposited(bytes32 indexed dealId, uint256 addedUsdc);
    event DealRefunded(bytes32 indexed dealId, uint256 refundAmount);
    event DealDisputed(bytes32 indexed dealId, address indexed initiator);
    event DisputeResolved(bytes32 indexed dealId, uint256 buyerRefund, uint256 sellerPayout);
    event Paused(address account);
    event Unpaused(address account);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == trustedOracleSigner, "Only trusted oracle");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }

    modifier nonReentrant() {
        require(_reentrancyStatus != 2, "ReentrancyGuard: reentrant call");
        _reentrancyStatus = 2;
        _;
        _reentrancyStatus = 1;
    }

    constructor(address _usdcToken, address _trustedOracle, address _pythAddress) {
        require(_usdcToken != address(0), "Invalid USDC address");
        require(_trustedOracle != address(0), "Invalid oracle address");
        owner = msg.sender;
        usdcToken = IERC20(_usdcToken);
        trustedOracleSigner = _trustedOracle;
        if (_pythAddress != address(0)) {
            pythOracle = IPyth(_pythAddress);
        }
        _reentrancyStatus = 1;
    }

    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    /**
     * @notice Create a dynamically backed mineral trade escrow.
     */
    function createDynamicDeal(
        bytes32 dealId,
        address seller,
        address inspector,
        uint256 totalAmountUsdc,
        uint256 collateralDepositUsdc,
        bytes32 pythPriceId,
        int64 basePriceUsd,
        uint256 minCollateralRatioBps,
        uint256 durationSeconds
    ) external whenNotPaused nonReentrant {
        require(deals[dealId].dealId == bytes32(0), "Deal exists");
        require(seller != address(0) && seller != msg.sender, "Invalid seller");
        require(inspector != address(0), "Invalid inspector");
        require(totalAmountUsdc > 0, "Invalid total amount");
        require(basePriceUsd > 0, "Base price must be positive");
        require(durationSeconds >= 60, "Duration must be at least 60s");

        uint256 requiredDeposit = totalAmountUsdc + collateralDepositUsdc;
        require(usdcToken.transferFrom(msg.sender, address(this), requiredDeposit), "USDC transfer failed");

        deals[dealId] = DynamicDeal({
            dealId: dealId,
            buyerAgent: msg.sender,
            sellerAgent: seller,
            inspector: inspector,
            totalAmountUsdc: totalAmountUsdc,
            collateralDepositUsdc: collateralDepositUsdc,
            pythPriceId: pythPriceId,
            basePriceUsd: basePriceUsd,
            minCollateralRatioBps: minCollateralRatioBps,
            oracleProofHash: bytes32(0),
            oracleProofVerified: false,
            carrierArrivalConfirmed: false,
            inspectorPurityPassed: false,
            expiryTimestamp: block.timestamp + durationSeconds,
            status: EscrowStatus.ACTIVE
        });

        emit DynamicDealCreated(dealId, msg.sender, seller, totalAmountUsdc, pythPriceId);
    }

    /**
     * @notice Oracle anchors compliance proof hash (EUDR, MOFCOM 0.1%, CBAM, etc.)
     */
    function anchorOracleProof(bytes32 dealId, bytes32 proofHash) external onlyOracle whenNotPaused {
        DynamicDeal storage deal = deals[dealId];
        require(
            deal.status == EscrowStatus.ACTIVE ||
            deal.status == EscrowStatus.CUSTOMS_CLEARED ||
            deal.status == EscrowStatus.MARGIN_CALLED,
            "Deal not active"
        );
        deal.oracleProofHash = proofHash;
        deal.oracleProofVerified = true;
        emit OracleProofAnchored(dealId, proofHash);
    }

    /**
     * @notice Carrier or Oracle confirms physical cargo arrival at port of discharge.
     */
    function confirmCarrierArrival(bytes32 dealId) external whenNotPaused {
        DynamicDeal storage deal = deals[dealId];
        require(msg.sender == trustedOracleSigner || msg.sender == owner, "Unauthorized carrier attestor");
        require(
            deal.status == EscrowStatus.ACTIVE ||
            deal.status == EscrowStatus.CUSTOMS_CLEARED ||
            deal.status == EscrowStatus.MARGIN_CALLED,
            "Deal not active"
        );
        deal.carrierArrivalConfirmed = true;
        emit CarrierArrivalNotified(dealId);
    }

    /**
     * @notice Independent inspector attests laboratory chemical assay purity (e.g., Cu >= 99.9935%).
     */
    function attestInspectorPurity(bytes32 dealId, bool passed) external whenNotPaused {
        DynamicDeal storage deal = deals[dealId];
        require(msg.sender == deal.inspector || msg.sender == trustedOracleSigner, "Unauthorized inspector");
        require(
            deal.status == EscrowStatus.ACTIVE ||
            deal.status == EscrowStatus.CUSTOMS_CLEARED ||
            deal.status == EscrowStatus.MARGIN_CALLED,
            "Deal not active"
        );
        deal.inspectorPurityPassed = passed;
        emit InspectorAttested(dealId, passed);
    }

    /**
     * @notice Oracle confirms customs clearance and battery passport verification at Port of Discharge.
     */
    function confirmCustomsClearance(bytes32 dealId) external onlyOracle whenNotPaused {
        DynamicDeal storage deal = deals[dealId];
        require(deal.status == EscrowStatus.ACTIVE, "Deal not active");
        deal.status = EscrowStatus.CUSTOMS_CLEARED;
        emit CustomsCleared(dealId);
    }

    /**
     * @notice Evaluate current market price via Pyth and trigger margin call if collateral falls below threshold.
     */
    function evaluateMarginCall(bytes32 dealId) external whenNotPaused {
        DynamicDeal storage deal = deals[dealId];
        require(deal.status == EscrowStatus.ACTIVE, "Deal not active");
        require(address(pythOracle) != address(0), "Pyth oracle not configured");
        require(deal.pythPriceId != bytes32(0), "Pyth price ID not set");

        IPyth.Price memory currentPrice = pythOracle.getPriceUnsafe(deal.pythPriceId);
        require(currentPrice.price > 0, "Invalid oracle price");
        require(currentPrice.publishTime > 0, "Invalid publish time");

        // If market price drops below initiation price, evaluate collateral buffer
        if (currentPrice.price < deal.basePriceUsd) {
            uint256 priceDrop = uint256(int256(deal.basePriceUsd - currentPrice.price));
            uint256 valueDropUsdc = (deal.totalAmountUsdc * priceDrop) / uint256(int256(deal.basePriceUsd));
            uint256 requiredCollateral = (valueDropUsdc * deal.minCollateralRatioBps) / 10000;

            if (deal.collateralDepositUsdc < requiredCollateral) {
                uint256 requiredTopup = requiredCollateral - deal.collateralDepositUsdc;
                deal.status = EscrowStatus.MARGIN_CALLED;
                emit MarginCallTriggered(dealId, currentPrice.price, requiredTopup);
            }
        }
    }

    /**
     * @notice Deposit additional collateral to cure a margin call or buffer against volatility.
     */
    function depositMarginTopup(bytes32 dealId, uint256 topupAmountUsdc) external whenNotPaused nonReentrant {
        DynamicDeal storage deal = deals[dealId];
        require(
            deal.status == EscrowStatus.ACTIVE || deal.status == EscrowStatus.MARGIN_CALLED,
            "Deal cannot accept topup"
        );
        require(topupAmountUsdc > 0, "Topup amount must be > 0");
        require(usdcToken.transferFrom(msg.sender, address(this), topupAmountUsdc), "USDC topup transfer failed");

        deal.collateralDepositUsdc += topupAmountUsdc;

        if (deal.status == EscrowStatus.MARGIN_CALLED) {
            deal.status = EscrowStatus.ACTIVE;
        }

        emit MarginTopupDeposited(dealId, topupAmountUsdc);
    }

    /**
     * @notice Tripartite settlement: Releases funds once all 3 conditions are satisfied.
     */
    function settleDeal(bytes32 dealId) external whenNotPaused nonReentrant {
        DynamicDeal storage deal = deals[dealId];
        require(
            deal.status == EscrowStatus.ACTIVE || deal.status == EscrowStatus.CUSTOMS_CLEARED,
            "Deal not active or cleared"
        );
        require(deal.oracleProofVerified, "Condition 1 missing: Oracle proof not verified");
        require(deal.carrierArrivalConfirmed, "Condition 2 missing: Carrier arrival unconfirmed");
        require(deal.inspectorPurityPassed, "Condition 3 missing: Laboratory assay failed");

        deal.status = EscrowStatus.RELEASED_SETTLED;

        // Payout seller the gross deal amount
        require(usdcToken.transfer(deal.sellerAgent, deal.totalAmountUsdc), "Payout transfer failed");
        
        // Return remaining collateral back to buyer
        if (deal.collateralDepositUsdc > 0) {
            require(usdcToken.transfer(deal.buyerAgent, deal.collateralDepositUsdc), "Collateral refund failed");
        }

        emit DealSettled(dealId, deal.totalAmountUsdc);
    }

    /**
     * @notice Refund buyer if deal expires before milestones are met.
     */
    function refundExpiredDeal(bytes32 dealId) external whenNotPaused nonReentrant {
        DynamicDeal storage deal = deals[dealId];
        require(
            deal.status == EscrowStatus.ACTIVE ||
            deal.status == EscrowStatus.MARGIN_CALLED ||
            deal.status == EscrowStatus.CUSTOMS_CLEARED,
            "Deal not active, margin called or customs cleared"
        );
        require(block.timestamp > deal.expiryTimestamp, "Deal not expired");

        deal.status = EscrowStatus.REFUNDED;
        uint256 totalRefund = deal.totalAmountUsdc + deal.collateralDepositUsdc;
        require(usdcToken.transfer(deal.buyerAgent, totalRefund), "Refund transfer failed");

        emit DealRefunded(dealId, totalRefund);
    }

    /**
     * @notice Buyer or seller raises a dispute regarding chemical assay, delivery or pricing.
     */
    function disputeDeal(bytes32 dealId) external whenNotPaused {
        DynamicDeal storage deal = deals[dealId];
        require(
            deal.status == EscrowStatus.ACTIVE ||
            deal.status == EscrowStatus.MARGIN_CALLED ||
            deal.status == EscrowStatus.CUSTOMS_CLEARED,
            "Cannot dispute current status"
        );
        require(
            msg.sender == deal.buyerAgent || msg.sender == deal.sellerAgent || msg.sender == owner,
            "Unauthorized party"
        );

        deal.status = EscrowStatus.DISPUTED;
        emit DealDisputed(dealId, msg.sender);
    }

    /**
     * @notice Oracle or contract owner arbitrates and resolves the dispute with precise fund split.
     */
    function resolveDispute(
        bytes32 dealId,
        uint256 buyerRefundUsdc,
        uint256 sellerPayoutUsdc
    ) external nonReentrant {
        DynamicDeal storage deal = deals[dealId];
        require(msg.sender == trustedOracleSigner || msg.sender == owner, "Only oracle or owner");
        require(deal.status == EscrowStatus.DISPUTED, "Deal not disputed");

        uint256 totalHeld = deal.totalAmountUsdc + deal.collateralDepositUsdc;
        require(buyerRefundUsdc + sellerPayoutUsdc == totalHeld, "Math mismatch: split != total held");

        deal.status = EscrowStatus.REFUNDED;

        if (buyerRefundUsdc > 0) {
            require(usdcToken.transfer(deal.buyerAgent, buyerRefundUsdc), "Buyer refund failed");
        }
        if (sellerPayoutUsdc > 0) {
            require(usdcToken.transfer(deal.sellerAgent, sellerPayoutUsdc), "Seller payout failed");
        }

        emit DisputeResolved(dealId, buyerRefundUsdc, sellerPayoutUsdc);
    }

    function setPythOracle(address _pyth) external onlyOwner {
        pythOracle = IPyth(_pyth);
    }

    function setTrustedOracle(address _oracle) external onlyOwner {
        require(_oracle != address(0), "Invalid oracle");
        trustedOracleSigner = _oracle;
    }
}
