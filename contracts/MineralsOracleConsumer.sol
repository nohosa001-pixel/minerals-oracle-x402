// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

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
    }

    event MineralPriceUpdated(string indexed symbol, uint256 spotPriceUsd, uint256 timestamp);
    event ScrapBatchSettled(string indexed scrapCategory, uint256 netValueUsd, uint256 quantityKg, address indexed agent);
}

/**
 * @title MineralsOracleConsumer
 * @author Minerals Oracle Team (Base Network)
 * @notice Production-grade Solidity consumer that verifies EIP-712 cryptographic proofs
 *         originating from the minerals-oracle-x402 micro-oracle on Base (Chain ID 8453).
 */
contract MineralsOracleConsumer is IMineralsOracleConsumer {
    // EIP-712 Typehashes
    bytes32 public constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant MINERAL_PRICE_TYPEHASH = keccak256(
        "MineralPriceFeed(string symbol,uint256 spotPriceUsd8Dec,uint256 timestamp,uint256 roundId)"
    );

    bytes32 public constant SCRAP_SETTLEMENT_TYPEHASH = keccak256(
        "ScrapSettlement(string scrapCategory,uint256 netValueUsd8Dec,uint256 quantityKg,uint256 timestamp)"
    );

    address public owner;
    address public trustedOracleSigner;
    uint256 public constant MAX_PRICE_STALENESS = 1 hours;

    // Latest verified feeds storage
    mapping(string => MineralPriceFeed) public latestPrices;
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
     * @notice Verifies and records an EIP-712 certified price feed on-chain.
     * @param feed The price feed payload signed by the oracle.
     * @param v ECDSA recovery id.
     * @param r ECDSA output r.
     * @param s ECDSA output s.
     */
    function updateMineralPrice(
        MineralPriceFeed calldata feed,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
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
        emit MineralPriceUpdated(feed.symbol, feed.spotPriceUsd8Dec, feed.timestamp);
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
     * @notice Retrieves verified spot price (8 decimals).
     */
    function getLatestPrice(string memory symbol) external view returns (uint256 priceUsd, uint256 updatedAt) {
        MineralPriceFeed memory feed = latestPrices[symbol];
        require(feed.timestamp > 0, "Price not available");
        return (feed.spotPriceUsd8Dec, feed.timestamp);
    }
}
