// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AggregatorV3Interface
 * @notice Standard Chainlink V3 Aggregator Interface for DeFi compatibility.
 */
interface AggregatorV3Interface {
    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
    function version() external view returns (uint256);

    function getRoundData(
        uint80 _roundId
    ) external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );

    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

/**
 * @title IMineralsOracleConsumer
 * @notice Interface for on-chain consumption and verification of minerals-oracle-x402 EIP-712 certified feeds.
 */
interface IMineralsOracleConsumer {
    struct MineralPriceFeed {
        string symbol;           // e.g., "Ag", "Pt", "Cu", "Li", "NdDy"
        uint256 spotPriceUsd8Dec; // Spot price with 8 decimals (e.g., $9650.00 -> 965000000000)
        uint256 timestamp;       // UTC timestamp
        uint256 roundId;         // Incremental sequence ID
    }

    struct ScrapSettlement {
        string scrapCategory;    // e.g., "EV_BATTERY_BLACK_MASS", "AUTO_CATALYST_CERAMIC"
        uint256 netValueUsd8Dec; // Net settlement value in USD (8 decimals)
        uint256 quantityKg;      // Scrap quantity in kilograms
        uint256 timestamp;       // Settlement timestamp
        bytes32 batchId;         // Unique recycling batch identifier
    }

    event MineralPriceUpdated(string indexed symbol, uint256 spotPriceUsd, uint256 roundId, uint256 timestamp);
    event ScrapBatchSettled(bytes32 indexed batchId, string indexed scrapCategory, uint256 netValueUsd, uint256 quantityKg, address indexed submitter);
}

/**
 * @title MineralsOracleConsumer
 * @author Minerals Oracle Team (Polygon Network)
 * @notice Production-grade Solidity consumer that verifies EIP-712 cryptographic proofs
 *         originating from minerals-oracle-x402 on Polygon (Chain ID 137 / Amoy 80002).
 *         Implements Chainlink AggregatorV3Interface compatibility for frictionless DeFi integration.
 */
contract MineralsOracleConsumer is IMineralsOracleConsumer, AggregatorV3Interface {
    // EIP-712 Typehashes
    bytes32 public constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant MINERAL_PRICE_TYPEHASH = keccak256(
        "MineralPriceFeed(string symbol,uint256 spotPriceUsd8Dec,uint256 timestamp,uint256 roundId)"
    );

    bytes32 public constant SCRAP_SETTLEMENT_TYPEHASH = keccak256(
        "ScrapSettlement(string scrapCategory,uint256 netValueUsd8Dec,uint256 quantityKg,uint256 timestamp,bytes32 batchId)"
    );

    uint8 public constant override decimals = 8;
    string public override description = "Minerals Oracle x402 - Critical Raw Minerals & Urban Mining Index";
    uint256 public constant override version = 1;

    address public owner;
    address public trustedOracleSigner;
    uint256 public constant MAX_PRICE_STALENESS = 2 hours;

    // Primary symbol for direct AggregatorV3Interface calls (default: "Cu" Copper)
    string public primaryBenchmarkSymbol = "Cu";

    // Latest verified feeds storage: symbol => MineralPriceFeed
    mapping(string => MineralPriceFeed) public latestPrices;
    
    // Historical round data: symbol => roundId => MineralPriceFeed
    mapping(string => mapping(uint256 => MineralPriceFeed)) public historicalRounds;

    // Settled scrap batches storage: batchId => ScrapSettlement
    mapping(bytes32 => ScrapSettlement) public settledBatches;
    
    // Anti-replay execution tracker
    mapping(bytes32 => bool) public executedAttestations;

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner permitted");
        _;
    }

    constructor(address _trustedOracleSigner) {
        require(_trustedOracleSigner != address(0), "Invalid oracle signer address");
        owner = msg.sender;
        trustedOracleSigner = _trustedOracleSigner;
    }

    /**
     * @notice Updates the trusted signer address.
     */
    function setTrustedOracleSigner(address _newSigner) external onlyOwner {
        require(_newSigner != address(0), "Invalid address");
        trustedOracleSigner = _newSigner;
    }

    /**
     * @notice Sets the primary default symbol for the AggregatorV3 interface.
     */
    function setPrimaryBenchmarkSymbol(string memory _symbol) external onlyOwner {
        primaryBenchmarkSymbol = _symbol;
    }

    /**
     * @notice Verifies and records an EIP-712 certified price feed on-chain.
     */
    function updateMineralPrice(
        MineralPriceFeed calldata feed,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        require(block.timestamp >= feed.timestamp, "Future timestamp rejected");
        require(block.timestamp - feed.timestamp <= MAX_PRICE_STALENESS, "Price feed is stale");

        bytes32 structHash = keccak256(
            abi.encode(
                MINERAL_PRICE_TYPEHASH,
                keccak256(bytes(feed.symbol)),
                feed.spotPriceUsd8Dec,
                feed.timestamp,
                feed.roundId
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        address recoveredSigner = ecrecover(digest, v, r, s);
        require(recoveredSigner == trustedOracleSigner, "Invalid EIP-712 oracle signature");

        bytes32 attestationKey = keccak256(abi.encodePacked(feed.symbol, feed.roundId));
        require(!executedAttestations[attestationKey], "Attestation already executed");
        executedAttestations[attestationKey] = true;

        latestPrices[feed.symbol] = feed;
        historicalRounds[feed.symbol][feed.roundId] = feed;

        emit MineralPriceUpdated(feed.symbol, feed.spotPriceUsd8Dec, feed.roundId, feed.timestamp);
    }

    /**
     * @notice Batch updates multiple mineral price feeds in a single atomic transaction.
     */
    function updateMineralPricesBatch(
        MineralPriceFeed[] calldata feeds,
        uint8[] calldata v,
        bytes32[] calldata r,
        bytes32[] calldata s
    ) external {
        uint256 len = feeds.length;
        require(len == v.length && len == r.length && len == s.length, "Array lengths mismatch");
        for (uint256 i = 0; i < len; i++) {
            updateMineralPrice(feeds[i], v[i], r[i], s[i]);
        }
    }

    /**
     * @notice Verifies and records an EIP-712 certified physical urban mining scrap settlement on-chain.
     */
    function settleScrapBatch(
        ScrapSettlement calldata settlement,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp >= settlement.timestamp, "Future timestamp rejected");
        require(settledBatches[settlement.batchId].timestamp == 0, "Batch already settled");

        bytes32 structHash = keccak256(
            abi.encode(
                SCRAP_SETTLEMENT_TYPEHASH,
                keccak256(bytes(settlement.scrapCategory)),
                settlement.netValueUsd8Dec,
                settlement.quantityKg,
                settlement.timestamp,
                settlement.batchId
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        address recoveredSigner = ecrecover(digest, v, r, s);
        require(recoveredSigner == trustedOracleSigner, "Invalid EIP-712 oracle signature");

        settledBatches[settlement.batchId] = settlement;
        emit ScrapBatchSettled(
            settlement.batchId,
            settlement.scrapCategory,
            settlement.netValueUsd8Dec,
            settlement.quantityKg,
            msg.sender
        );
    }

    /**
     * @notice Computes domain separator for EIP-712 verification.
     */
    function _hashTypedDataV4(bytes32 structHash) internal view returns (bytes32) {
        bytes32 domainSeparator = keccak256(
            abi.encode(
                DOMAIN_TYPEHASH,
                keccak256(bytes("MineralsOracle")),
                keccak256(bytes("1.0.0")),
                block.chainid,
                address(this)
            )
        );
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator, structHash));
    }

    /**
     * @notice Chainlink standard latestRoundData implementation for primary benchmark symbol.
     */
    function latestRoundData() external view override returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    ) {
        return getLatestRoundDataForSymbol(primaryBenchmarkSymbol);
    }

    /**
     * @notice Chainlink standard getRoundData implementation for historical round queries.
     */
    function getRoundData(
        uint80 _roundId
    ) external view override returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    ) {
        MineralPriceFeed memory feed = historicalRounds[primaryBenchmarkSymbol][_roundId];
        require(feed.timestamp > 0, "Round data not found");
        return (
            _roundId,
            int256(feed.spotPriceUsd8Dec),
            feed.timestamp,
            feed.timestamp,
            _roundId
        );
    }

    /**
     * @notice Specific Chainlink-format round query for any mineral symbol (Ag, Pt, Cu, Li, NdDy).
     */
    function getLatestRoundDataForSymbol(string memory symbol) public view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    ) {
        MineralPriceFeed memory feed = latestPrices[symbol];
        require(feed.timestamp > 0, "Price not available");
        uint80 rId = uint80(feed.roundId);
        return (
            rId,
            int256(feed.spotPriceUsd8Dec),
            feed.timestamp,
            feed.timestamp,
            rId
        );
    }

    /**
     * @notice Simple getter for latest verified spot price (8 decimals).
     */
    function getLatestPrice(string memory symbol) external view returns (uint256 priceUsd, uint256 updatedAt) {
        MineralPriceFeed memory feed = latestPrices[symbol];
        require(feed.timestamp > 0, "Price not available");
        return (feed.spotPriceUsd8Dec, feed.timestamp);
    }
}
