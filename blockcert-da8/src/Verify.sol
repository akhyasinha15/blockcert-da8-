// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// DA-1 Question 1 (unchanged) - 23BKT0045 / AKHYA SINHA
// First-generation hash-linked certificate chain. Superseded in DA-8 by
// CertificateRegistry, which keeps the same hash-chain idea and adds issuer
// roles, IPFS references, revocation and tamper auditing.
contract Verify {
    address public admin;

    struct Certificate {
        string certId;
        string studentName;
        string degree;
        uint256 yearOfGraduation;
        bytes32 dataHash;
        bytes32 previousHash;
        uint256 timestamp;
        bool exists;
    }

    Certificate[] public certificateChain;
    mapping(string => Certificate) private certificates;

    event CertificateAdded(
        string indexed certId,
        string studentName,
        bytes32 blockHash,
        bytes32 previousHash
    );
    event TamperAlert(string certId, string message);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Access Denied: Only admin can perform this operation.");
        _;
    }

    constructor() {
        admin = msg.sender;
        _createGenesisBlock();
    }

    function _createGenesisBlock() private {
        bytes32 genesisHash = keccak256(abi.encodePacked("GENESIS_BLOCK", block.timestamp));

        Certificate memory genesisCert = Certificate({
            certId: "0000",
            studentName: "Genesis Block",
            degree: "N/A",
            yearOfGraduation: 0,
            dataHash: genesisHash,
            previousHash: bytes32(0),
            timestamp: block.timestamp,
            exists: true
        });

        certificateChain.push(genesisCert);
        certificates["0000"] = genesisCert;
    }

    function calculateCertificateHash(
        string memory _certId,
        string memory _studentName,
        string memory _degree,
        uint256 _yearOfGraduation,
        bytes32 _previousHash
    ) public pure returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                _certId,
                _studentName,
                _degree,
                _yearOfGraduation,
                _previousHash
            )
        );
    }

    function addCertificate(
        string memory _certId,
        string memory _studentName,
        string memory _degree,
        uint256 _yearOfGraduation
    ) public onlyAdmin {
        require(!certificates[_certId].exists, "Error: Certificate ID already exists!");

        bytes32 lastHash = certificateChain[certificateChain.length - 1].dataHash;
        bytes32 currentHash = calculateCertificateHash(
            _certId,
            _studentName,
            _degree,
            _yearOfGraduation,
            lastHash
        );

        Certificate memory newCert = Certificate({
            certId: _certId,
            studentName: _studentName,
            degree: _degree,
            yearOfGraduation: _yearOfGraduation,
            dataHash: currentHash,
            previousHash: lastHash,
            timestamp: block.timestamp,
            exists: true
        });

        certificateChain.push(newCert);
        certificates[_certId] = newCert;

        emit CertificateAdded(_certId, _studentName, currentHash, lastHash);
    }

    function getCertificate(string memory _certId)
        public
        view
        returns (
            string memory studentName,
            string memory degree,
            uint256 yearOfGraduation,
            bytes32 dataHash,
            bytes32 previousHash,
            uint256 timestamp
        )
    {
        require(certificates[_certId].exists, "Certificate does not exist.");
        Certificate memory cert = certificates[_certId];
        return (
            cert.studentName,
            cert.degree,
            cert.yearOfGraduation,
            cert.dataHash,
            cert.previousHash,
            cert.timestamp
        );
    }

    function verifyChainIntegrity() public view returns (bool isValid) {
        for (uint256 i = 1; i < certificateChain.length; i++) {
            Certificate memory current = certificateChain[i];
            Certificate memory previous = certificateChain[i - 1];

            bytes32 expectedHash = calculateCertificateHash(
                current.certId,
                current.studentName,
                current.degree,
                current.yearOfGraduation,
                current.previousHash
            );

            if (current.dataHash != expectedHash) {
                return false;
            }

            if (current.previousHash != previous.dataHash) {
                return false;
            }
        }
        return true;
    }

    function getTotalCertificates() public view returns (uint256) {
        return certificateChain.length;
    }
}
