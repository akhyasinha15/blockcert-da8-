// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Minimal view of the DA-1 DigitalIdentity contract used for identity checks.
interface IDigitalIdentity {
    function isWalletRegistered(address _walletAddress) external view returns (bool);
}

/// @title CertificateRegistry
/// @author AKHYA SINHA (23BKT0045)
/// @notice DA-8 integrated module. Combines the DA-1 hash-linked certificate chain (Verify.sol)
///         with the DA-1 wallet identity registry (DigitalIdentity.sol):
///           * only wallets registered in DigitalIdentity AND authorised by the admin can issue,
///           * every certificate is a block linked to the previous block by its hash,
///           * the certificate PDF/metadata lives off-chain (IPFS) and is referenced by CID,
///           * certificates can be revoked without rewriting history,
///           * anyone can verify a claimed certificate and audit the whole chain for tampering.
contract CertificateRegistry {
    // ------------------------------------------------------------------ data structures
    struct CertBlock {
        string certId;
        string studentName;
        string degree;
        uint16 yearOfGraduation;
        string ipfsCid;        // off-chain document reference
        address issuer;        // wallet that issued the certificate
        bytes32 dataHash;      // hash of this block (covers data + previousHash)
        bytes32 previousHash;  // dataHash of the previous block
        uint64 timestamp;
        bool revoked;          // status flag - deliberately NOT part of the hash
    }

    // ------------------------------------------------------------------ state
    address public immutable admin;
    IDigitalIdentity public immutable identity;

    mapping(address => bool) public isIssuer;

    CertBlock[] internal chain;
    mapping(bytes32 => uint256) internal indexPlusOne; // keccak256(certId) => chain index + 1

    // ------------------------------------------------------------------ events
    event IssuerAuthorized(address indexed issuer);
    event IssuerRevoked(address indexed issuer);
    event CertificateIssued(
        uint256 indexed index,
        string certId,
        string studentName,
        address indexed issuer,
        bytes32 blockHash,
        bytes32 previousHash,
        string ipfsCid
    );
    event CertificateRevoked(string certId, address indexed revokedBy, string reason);
    event TamperAlert(uint256 indexed index, string certId, string message);

    // ------------------------------------------------------------------ access control
    modifier onlyAdmin() {
        require(msg.sender == admin, "Access Denied: Only admin can perform this operation.");
        _;
    }

    modifier onlyIssuer() {
        require(isIssuer[msg.sender], "Access Denied: Caller is not an authorised issuer.");
        _;
    }

    // ------------------------------------------------------------------ constructor
    constructor(address _identityContract) {
        require(_identityContract != address(0), "Error: Identity contract address required.");
        admin = msg.sender;
        identity = IDigitalIdentity(_identityContract);
        _createGenesisBlock();
    }

    function _genesisHash() private view returns (bytes32) {
        return keccak256(abi.encode("BLOCKCERT_GENESIS", address(this)));
    }

    function _createGenesisBlock() private {
        chain.push(
            CertBlock({
                certId: "GENESIS",
                studentName: "Genesis Block",
                degree: "N/A",
                yearOfGraduation: 0,
                ipfsCid: "",
                issuer: msg.sender,
                dataHash: _genesisHash(),
                previousHash: bytes32(0),
                timestamp: uint64(block.timestamp),
                revoked: false
            })
        );
        indexPlusOne[keccak256(bytes("GENESIS"))] = 1;
    }

    // ------------------------------------------------------------------ issuer management
    function authorizeIssuer(address _issuer) external onlyAdmin {
        require(
            identity.isWalletRegistered(_issuer),
            "Error: Issuer must have a registered digital identity."
        );
        require(!isIssuer[_issuer], "Error: Already an issuer.");
        isIssuer[_issuer] = true;
        emit IssuerAuthorized(_issuer);
    }

    function revokeIssuer(address _issuer) external onlyAdmin {
        require(isIssuer[_issuer], "Error: Not an issuer.");
        isIssuer[_issuer] = false;
        emit IssuerRevoked(_issuer);
    }

    // ------------------------------------------------------------------ hashing
    /// @dev abi.encode (not encodePacked) so ("AB","C") and ("A","BC") can never collide.
    function computeHash(
        string memory _certId,
        string memory _studentName,
        string memory _degree,
        uint16 _year,
        string memory _ipfsCid,
        bytes32 _previousHash
    ) public pure returns (bytes32) {
        return keccak256(abi.encode(_certId, _studentName, _degree, _year, _ipfsCid, _previousHash));
    }

    // ------------------------------------------------------------------ issuing / revoking
    function issueCertificate(
        string calldata _certId,
        string calldata _studentName,
        string calldata _degree,
        uint16 _year,
        string calldata _ipfsCid
    ) external onlyIssuer returns (bytes32 blockHash) {
        require(bytes(_certId).length > 0, "Error: Certificate ID is required.");
        require(bytes(_studentName).length > 0, "Error: Student name is required.");
        require(_year >= 1950 && _year <= 2100, "Error: Invalid graduation year.");
        require(indexPlusOne[keccak256(bytes(_certId))] == 0, "Error: Certificate ID already exists!");

        bytes32 prev = chain[chain.length - 1].dataHash;
        blockHash = computeHash(_certId, _studentName, _degree, _year, _ipfsCid, prev);

        chain.push(
            CertBlock({
                certId: _certId,
                studentName: _studentName,
                degree: _degree,
                yearOfGraduation: _year,
                ipfsCid: _ipfsCid,
                issuer: msg.sender,
                dataHash: blockHash,
                previousHash: prev,
                timestamp: uint64(block.timestamp),
                revoked: false
            })
        );
        indexPlusOne[keccak256(bytes(_certId))] = chain.length;

        emit CertificateIssued(chain.length - 1, _certId, _studentName, msg.sender, blockHash, prev, _ipfsCid);
    }

    function revokeCertificate(string calldata _certId, string calldata _reason) external {
        uint256 i = _indexOf(_certId);
        CertBlock storage c = chain[i];
        require(msg.sender == c.issuer || msg.sender == admin, "Access Denied: Only issuer or admin can revoke.");
        require(!c.revoked, "Error: Certificate already revoked.");
        c.revoked = true;
        emit CertificateRevoked(_certId, msg.sender, _reason);
    }

    // ------------------------------------------------------------------ queries
    function getCertificate(string calldata _certId) external view returns (CertBlock memory) {
        return chain[_indexOf(_certId)];
    }

    function getBlock(uint256 _index) external view returns (CertBlock memory) {
        require(_index < chain.length, "Error: Block index out of range.");
        return chain[_index];
    }

    function totalBlocks() external view returns (uint256) {
        return chain.length;
    }

    /// @notice Employer-style check: do the claimed details match what was issued?
    /// @return authentic true if the claimed details hash to the stored block hash
    /// @return revoked   true if the issuer has revoked the certificate
    /// @return issuer    wallet that issued it (zero address if unknown)
    function verifyCertificate(
        string calldata _certId,
        string calldata _studentName,
        string calldata _degree,
        uint16 _year
    ) external view returns (bool authentic, bool revoked, address issuer) {
        uint256 idx = indexPlusOne[keccak256(bytes(_certId))];
        if (idx == 0) return (false, false, address(0));
        CertBlock storage c = chain[idx - 1];
        bytes32 h = computeHash(_certId, _studentName, _degree, _year, c.ipfsCid, c.previousHash);
        return (h == c.dataHash, c.revoked, c.issuer);
    }

    // ------------------------------------------------------------------ tamper detection
    /// @notice Re-computes every block hash and checks every previousHash link.
    /// @return valid true if the whole chain is consistent
    /// @return badIndex index of the first inconsistent block (0 if valid)
    function verifyChainIntegrity() public view returns (bool valid, uint256 badIndex) {
        if (chain[0].dataHash != _genesisHash()) return (false, 0);
        for (uint256 i = 1; i < chain.length; i++) {
            CertBlock storage cur = chain[i];
            bytes32 expected = computeHash(
                cur.certId, cur.studentName, cur.degree, cur.yearOfGraduation, cur.ipfsCid, cur.previousHash
            );
            if (cur.dataHash != expected || cur.previousHash != chain[i - 1].dataHash) {
                return (false, i);
            }
        }
        return (true, 0);
    }

    /// @notice State-changing audit that leaves an on-chain TamperAlert when the chain is broken.
    function auditChain() external returns (bool valid) {
        uint256 bad;
        (valid, bad) = verifyChainIntegrity();
        if (!valid) {
            emit TamperAlert(bad, chain[bad].certId, "Blockchain compromised: block hash or link mismatch.");
        }
    }

    // ------------------------------------------------------------------ internals
    function _indexOf(string memory _certId) internal view returns (uint256) {
        uint256 idx = indexPlusOne[keccak256(bytes(_certId))];
        require(idx != 0, "Certificate does not exist.");
        return idx - 1;
    }
}
