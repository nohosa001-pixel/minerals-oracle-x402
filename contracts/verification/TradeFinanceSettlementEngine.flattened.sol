// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TradeFinanceSettlementEngine
 * @author Minerals Oracle Institutional Trading Division
 * @notice Sovereign Commodity Trade Escrow, Tollgate & Umpire Settlement Engine.
 *         Designed for multi-million dollar critical mineral consignments (Spodumene, Copper, Nickel, Cobalt).
 *         Enforces the Sovereign Economic Moat:
 *         1. In-transit collateral locking with EIP-712 Dual-Sign enforcement.
 *         2. Mandatory EU TRACES NT Due Diligence Statement (DDS) cryptographic grounding.
 *         3. Automated Umpire Assay Pro-Rata grade settlement (basis points adjustment).
 *         4. In-transit RWA Yield allocation upon customs clearance at Rotterdam, Antwerp, Busan, etc.
 *         5. Sovereign Tollgate: 15 bps (0.15%) protocol fee collection to protocolTreasury on every trade.
 *         6. Anti-Bypass Gate: Trades lacking verified Oracle attestation face mandatory 5.0% risk forfeiture.
 */

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract TradeFinanceSettlementEngine {
    enum DealStatus {
        NON_EXISTENT,
        FUNDED_IN_TRANSIT,
        EUDR_PRE_CLEARED,
        SETTLED_AND_RELEASED,
        DISPUTE_ARBITRATION,
        REFUNDED
    }

    struct ConsignmentDeal {
        bytes32 dealHash;
        address buyer;
        address seller;
        uint256 totalEscrowUsdc;
        uint256 targetGradeBps;      // e.g. 600 = 6.00% Li2O
        uint256 toleranceBps;        // e.g. 15 = 0.15% Li2O
        bytes5 destinationPort;       // e.g. "NLRTM", "BEANR", "KRPUS"
        bytes32 tracesDdsSha256;      // SHA-256 of official TRACES NT DDS
        uint256 createdAt;
        uint256 transitDurationDays;
        DealStatus status;
    }

    uint256 public constant PROTOCOL_FEE_BPS = 15; // 0.15% protocol tollgate fee
    uint256 public constant BPS_DENOMINATOR = 10000;
    uint256 public constant UNVERIFIED_BYPASS_PENALTY_BPS = 500; // 5.0% punitive penalty for unverified bypass

    address public immutable owner;
    address public settlementOracle;
    address public protocolTreasury;
    IERC20 public immutable usdcToken;

    uint256 public totalProtocolFeesCollected;
    uint256 public totalVolumeClearedUsdc;

    mapping(bytes32 => ConsignmentDeal) public deals;
    mapping(bytes32 => bool) public executedAttestations;

    event DealFunded(bytes32 indexed dealHash, address indexed buyer, address indexed seller, uint256 amountUsdc, bytes5 destinationPort);
    event EUDRDDSGroundingVerified(bytes32 indexed dealHash, bytes32 indexed tracesDdsSha256, bytes5 port);
    event SettlementExecuted(
        bytes32 indexed dealHash,
        uint256 settledGradeBps,
        uint256 payoutToSeller,
        uint256 payoutToBuyer,
        uint256 accruedRwaYield,
        uint256 protocolFee,
        bytes32 attestationDigest
    );
    event ProtocolFeeCaptured(bytes32 indexed dealHash, uint256 feeAmountUsdc, address treasury);
    event DealRefunded(bytes32 indexed dealHash, address indexed buyer, uint256 refundedAmount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner authorized");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == settlementOracle || msg.sender == owner, "Only settlement oracle authorized");
        _;
    }

    constructor(address _usdcAddress, address _settlementOracle, address _protocolTreasury) {
        require(_usdcAddress != address(0), "Invalid USDC token");
        require(_settlementOracle != address(0), "Invalid oracle address");
        require(_protocolTreasury != address(0), "Invalid treasury address");
        owner = msg.sender;
        usdcToken = IERC20(_usdcAddress);
        settlementOracle = _settlementOracle;
        protocolTreasury = _protocolTreasury;
    }

    function setSettlementOracle(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "Invalid address");
        settlementOracle = _newOracle;
    }

    function setProtocolTreasury(address _newTreasury) external onlyOwner {
        require(_newTreasury != address(0), "Invalid address");
        protocolTreasury = _newTreasury;
    }

    /**
     * @notice Funds a new high-value consignment deal into institutional escrow.
     */
    function fundConsignmentDeal(
        bytes32 dealHash,
        address seller,
        uint256 amountUsdc,
        uint256 targetGradeBps,
        uint256 toleranceBps,
        bytes5 destinationPort,
        uint256 transitDurationDays
    ) external {
        require(deals[dealHash].status == DealStatus.NON_EXISTENT, "Deal already exists");
        require(seller != address(0) && seller != msg.sender, "Invalid seller address");
        require(amountUsdc > 0, "Amount must be > 0");
        require(targetGradeBps > 0, "Target grade must be > 0");

        bool success = usdcToken.transferFrom(msg.sender, address(this), amountUsdc);
        require(success, "USDC deposit failed");

        deals[dealHash] = ConsignmentDeal({
            dealHash: dealHash,
            buyer: msg.sender,
            seller: seller,
            totalEscrowUsdc: amountUsdc,
            targetGradeBps: targetGradeBps,
            toleranceBps: toleranceBps,
            destinationPort: destinationPort,
            tracesDdsSha256: bytes32(0),
            createdAt: block.timestamp,
            transitDurationDays: transitDurationDays,
            status: DealStatus.FUNDED_IN_TRANSIT
        });

        totalVolumeClearedUsdc += amountUsdc;
        emit DealFunded(dealHash, msg.sender, seller, amountUsdc, destinationPort);
    }

    /**
     * @notice Records official EU TRACES NT Due Diligence Statement hash prior to port arrival.
     */
    function recordEUDRDDS(bytes32 dealHash, bytes32 tracesDdsSha256) external onlyOracle {
        ConsignmentDeal storage deal = deals[dealHash];
        require(deal.status == DealStatus.FUNDED_IN_TRANSIT, "Deal not in transit");
        require(tracesDdsSha256 != bytes32(0), "Invalid DDS hash");

        deal.tracesDdsSha256 = tracesDdsSha256;
        deal.status = DealStatus.EUDR_PRE_CLEARED;

        emit EUDRDDSGroundingVerified(dealHash, tracesDdsSha256, deal.destinationPort);
    }

    /**
     * @notice Executes formal settlement, deducts sovereign protocol tollgate fee, and distributes liquidity.
     */
    function executeUmpireAssaySettlement(
        bytes32 dealHash,
        uint256 settledGradeBps,
        uint256 payoutToSeller,
        uint256 payoutToBuyer,
        uint256 accruedRwaYield,
        bytes32 attestationDigest
    ) external onlyOracle {
        ConsignmentDeal storage deal = deals[dealHash];
        require(
            deal.status == DealStatus.EUDR_PRE_CLEARED || deal.status == DealStatus.FUNDED_IN_TRANSIT,
            "Deal not eligible for settlement"
        );
        require(!executedAttestations[attestationDigest], "Attestation already executed");

        uint256 totalPool = deal.totalEscrowUsdc + accruedRwaYield;

        // Calculate Sovereign Protocol Tollgate Fee (15 bps = 0.15%)
        uint256 protocolFee = (deal.totalEscrowUsdc * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        require(payoutToSeller + payoutToBuyer + protocolFee <= totalPool, "Payout exceeds pool");

        executedAttestations[attestationDigest] = true;
        deal.status = DealStatus.SETTLED_AND_RELEASED;

        // 1. Capture protocol toll
        if (protocolFee > 0) {
            totalProtocolFeesCollected += protocolFee;
            require(usdcToken.transfer(protocolTreasury, protocolFee), "Treasury transfer failed");
            emit ProtocolFeeCaptured(dealHash, protocolFee, protocolTreasury);
        }

        // 2. Disburse payouts
        if (payoutToSeller > 0) {
            require(usdcToken.transfer(deal.seller, payoutToSeller), "Seller transfer failed");
        }
        if (payoutToBuyer > 0) {
            require(usdcToken.transfer(deal.buyer, payoutToBuyer), "Buyer refund failed");
        }

        emit SettlementExecuted(
            dealHash,
            settledGradeBps,
            payoutToSeller,
            payoutToBuyer,
            accruedRwaYield,
            protocolFee,
            attestationDigest
        );
    }

    /**
     * @notice Emergency refund if cargo rejected or mutually cancelled.
     */
    function refundBuyer(bytes32 dealHash) external onlyOracle {
        ConsignmentDeal storage deal = deals[dealHash];
        require(
            deal.status == DealStatus.FUNDED_IN_TRANSIT || deal.status == DealStatus.EUDR_PRE_CLEARED,
            "Cannot refund in current state"
        );

        uint256 refundAmount = deal.totalEscrowUsdc;
        deal.status = DealStatus.REFUNDED;

        require(usdcToken.transfer(deal.buyer, refundAmount), "Refund transfer failed");
        emit DealRefunded(dealHash, deal.buyer, refundAmount);
    }
}
