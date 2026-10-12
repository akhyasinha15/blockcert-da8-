// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {TestBase, Vm} from "./TestBase.sol";
import {DigitalIdentity} from "../src/DigitalIdentity.sol";
import {CertificateRegistry} from "../src/CertificateRegistry.sol";
import {RegistryHarness} from "./mocks/RegistryHarness.sol";

contract CertificateRegistryTest is TestBase {
    DigitalIdentity id;
    CertificateRegistry reg;
    RegistryHarness harness;

    address admin = address(this);
    address registrar = address(0xA11CE); // university registrar (issuer)
    address stranger = address(0xBAD);    // wallet that never registered an identity

    string constant CID1 = "QmTestCid1";
    string constant CID2 = "QmTestCid2";

    function setUp() public {
        id = new DigitalIdentity();
        reg = new CertificateRegistry(address(id));
        harness = new RegistryHarness(address(id));

        vm.prank(registrar);
        id.registerUser(1, "Registrar Office", "Academic Affairs");

        reg.authorizeIssuer(registrar);
        harness.authorizeIssuer(registrar);
    }

    function _issue(CertificateRegistry r, string memory certId, string memory name) internal {
        vm.prank(registrar);
        r.issueCertificate(certId, name, "B.Tech Computer Science", 2027, CID1);
    }

    // ---- T01 genesis ----------------------------------------------------------------
    function test_T01_GenesisBlockCreated() public view {
        assertEq(reg.totalBlocks(), 1, "chain must start with genesis");
        CertificateRegistry.CertBlock memory g = reg.getBlock(0);
        assertEq(g.certId, "GENESIS", "genesis id");
        assertEq(g.previousHash, bytes32(0), "genesis previousHash is zero");
        (bool ok,) = reg.verifyChainIntegrity();
        assertTrue(ok, "fresh chain is valid");
    }

    // ---- T02 issuer rules -----------------------------------------------------------
    function test_T02_AuthorizeRequiresRegisteredIdentity() public {
        vm.expectRevert(revertMsg("Error: Issuer must have a registered digital identity."));
        reg.authorizeIssuer(stranger);
    }

    function test_T03_OnlyAdminCanAuthorize() public {
        vm.prank(registrar);
        vm.expectRevert(revertMsg("Access Denied: Only admin can perform this operation."));
        reg.authorizeIssuer(registrar);
    }

    function test_T04_NonIssuerCannotIssue() public {
        vm.prank(stranger);
        vm.expectRevert(revertMsg("Access Denied: Caller is not an authorised issuer."));
        reg.issueCertificate("CERT-1", "ALICE", "B.Tech", 2027, CID1);
    }

    function test_T05_RevokedIssuerCannotIssue() public {
        reg.revokeIssuer(registrar);
        vm.prank(registrar);
        vm.expectRevert(revertMsg("Access Denied: Caller is not an authorised issuer."));
        reg.issueCertificate("CERT-1", "ALICE", "B.Tech", 2027, CID1);
    }

    // ---- T06 issuing ----------------------------------------------------------------
    function test_T06_IssueLinksBlocks() public {
        _issue(reg, "CERT-101", "ALICE");
        _issue(reg, "CERT-102", "BOB");
        assertEq(reg.totalBlocks(), 3, "genesis + 2");
        CertificateRegistry.CertBlock memory b1 = reg.getBlock(1);
        CertificateRegistry.CertBlock memory b2 = reg.getBlock(2);
        assertEq(b1.previousHash, reg.getBlock(0).dataHash, "block1 links to genesis");
        assertEq(b2.previousHash, b1.dataHash, "block2 links to block1");
        assertEq(
            b2.dataHash,
            reg.computeHash("CERT-102", "BOB", "B.Tech Computer Science", 2027, CID1, b1.dataHash),
            "stored hash equals recomputed hash"
        );
    }

    function test_T07_DuplicateCertIdReverts() public {
        _issue(reg, "CERT-101", "ALICE");
        vm.prank(registrar);
        vm.expectRevert(revertMsg("Error: Certificate ID already exists!"));
        reg.issueCertificate("CERT-101", "MALLORY", "B.Tech", 2027, CID2);
    }

    function test_T08_InvalidYearReverts() public {
        vm.prank(registrar);
        vm.expectRevert(revertMsg("Error: Invalid graduation year."));
        reg.issueCertificate("CERT-9", "ALICE", "B.Tech", 1800, CID1);
    }

    // ---- T09 verification -----------------------------------------------------------
    function test_T09_VerifyAuthenticCertificate() public {
        _issue(reg, "CERT-101", "ALICE");
        (bool authentic, bool revoked, address issuer) =
            reg.verifyCertificate("CERT-101", "ALICE", "B.Tech Computer Science", 2027);
        assertTrue(authentic, "genuine details must verify");
        assertTrue(!revoked, "not revoked");
        assertEq(issuer, registrar, "issuer recorded");
    }

    function test_T10_VerifyDetectsForgedDetails() public {
        _issue(reg, "CERT-101", "ALICE");
        (bool authentic,,) = reg.verifyCertificate("CERT-101", "ALICE", "B.Tech Computer Science", 2028);
        assertTrue(!authentic, "altered year must fail");
        (authentic,,) = reg.verifyCertificate("CERT-101", "MALLORY", "B.Tech Computer Science", 2027);
        assertTrue(!authentic, "altered name must fail");
        (authentic,,) = reg.verifyCertificate("CERT-404", "ALICE", "B.Tech Computer Science", 2027);
        assertTrue(!authentic, "unknown id must fail");
    }

    // ---- T11 revocation -------------------------------------------------------------
    function test_T11_RevokeCertificate() public {
        _issue(reg, "CERT-101", "ALICE");
        vm.prank(registrar);
        reg.revokeCertificate("CERT-101", "Degree withdrawn");
        (bool authentic, bool revoked,) = reg.verifyCertificate("CERT-101", "ALICE", "B.Tech Computer Science", 2027);
        assertTrue(authentic, "history is preserved");
        assertTrue(revoked, "flag set");
        (bool ok,) = reg.verifyChainIntegrity();
        assertTrue(ok, "revocation must not break the chain");
    }

    function test_T12_StrangerCannotRevoke() public {
        _issue(reg, "CERT-101", "ALICE");
        vm.prank(stranger);
        vm.expectRevert(revertMsg("Access Denied: Only issuer or admin can revoke."));
        reg.revokeCertificate("CERT-101", "vandalism");
    }

    // ---- T13 chain integrity --------------------------------------------------------
    function test_T13_ChainValidAfterManyCertificates() public {
        for (uint256 i = 0; i < 8; i++) {
            _issue(reg, string(abi.encodePacked("CERT-", bytes1(uint8(48 + i)))), "STUDENT");
        }
        (bool ok, uint256 bad) = reg.verifyChainIntegrity();
        assertTrue(ok, "8 certificates, chain valid");
        assertEq(bad, 0, "no bad index");
    }

    // ---- T14/T15 tamper detection ---------------------------------------------------
    function test_T14_TamperedRecordDetected() public {
        _issue(harness, "CERT-101", "ALICE");
        _issue(harness, "CERT-102", "BOB");
        _issue(harness, "CERT-103", "CHARLIE");

        harness.corruptStudentName(2, "MALLORY"); // silent edit of BOB's record

        (bool ok, uint256 bad) = harness.verifyChainIntegrity();
        assertTrue(!ok, "tampering must be detected");
        assertEq(bad, 2, "first bad block is the edited one");
    }

    function test_T15_TamperedHashBreaksLink() public {
        _issue(harness, "CERT-101", "ALICE");
        _issue(harness, "CERT-102", "BOB");

        // attacker rewrites a block hash to hide an edit -> next block's link no longer matches
        harness.corruptDataHash(1, keccak256("forged"));

        (bool ok, uint256 bad) = harness.verifyChainIntegrity();
        assertTrue(!ok, "forged hash detected");
        assertEq(bad, 1, "detected at the forged block");
    }

    function test_T16_AuditEmitsTamperAlert() public {
        _issue(harness, "CERT-101", "ALICE");
        harness.corruptStudentName(1, "MALLORY");

        vm.recordLogs();
        bool valid = harness.auditChain();
        Vm.Log[] memory logs = vm.getRecordedLogs();

        assertTrue(!valid, "audit reports invalid");
        assertEq(logs.length, 1, "exactly one event");
        assertEq(logs[0].topics[0], keccak256("TamperAlert(uint256,string,string)"), "TamperAlert emitted");
    }
}
