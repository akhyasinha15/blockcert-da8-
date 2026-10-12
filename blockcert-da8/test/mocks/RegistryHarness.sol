// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {CertificateRegistry} from "../../src/CertificateRegistry.sol";

/// @notice TEST-ONLY. Real deployments are append-only, so tampering cannot happen through the
///         public API. This harness exposes raw storage writes to simulate a corrupted node /
///         compromised database so the tamper-detection logic can be demonstrated.
contract RegistryHarness is CertificateRegistry {
    constructor(address _identity) CertificateRegistry(_identity) {}

    function corruptStudentName(uint256 i, string calldata newName) external {
        chain[i].studentName = newName;
    }

    function corruptDataHash(uint256 i, bytes32 newHash) external {
        chain[i].dataHash = newHash;
    }
}
