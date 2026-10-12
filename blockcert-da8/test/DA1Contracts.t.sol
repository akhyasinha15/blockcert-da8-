// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {TestBase} from "./TestBase.sol";
import {DigitalIdentity} from "../src/DigitalIdentity.sol";
import {Verify} from "../src/Verify.sol";

/// Regression tests proving the DA-1 contracts still behave as submitted.
contract DA1ContractsTest is TestBase {
    DigitalIdentity id;
    Verify verify;

    address alice = address(0xA1);
    address bob = address(0xB2);
    address charlie = address(0xC3);

    function setUp() public {
        id = new DigitalIdentity();
        verify = new Verify();
    }

    function test_DA1_RegisterThreeUsers() public {
        vm.prank(alice);
        id.registerUser(101, "ALICE", "COMPUTER SCIENCE BLOCKCHAIN");
        vm.prank(bob);
        id.registerUser(102, "BOB", "DATA SCIENCE");
        vm.prank(charlie);
        id.registerUser(103, "CHARLIE", "CYBER SECURITY");
        assertEq(id.totalRegisteredUsers(), 3, "three users");
        (uint256 uid, string memory name,) = id.getUser(charlie);
        assertEq(uid, 103, "id");
        assertEq(name, "CHARLIE", "name");
        assertTrue(id.isWalletRegistered(alice), "alice registered");
        assertTrue(!id.isWalletRegistered(address(0xD4)), "dave not registered");
    }

    function test_DA1_DuplicateWalletReverts() public {
        vm.startPrank(alice);
        id.registerUser(101, "ALICE", "CS");
        vm.expectRevert(revertMsg("Error: Wallet address is already registered."));
        id.registerUser(104, "ALICE AGAIN", "CS");
        vm.stopPrank();
    }

    function test_DA1_ZeroUserIdReverts() public {
        vm.prank(address(0xD4));
        vm.expectRevert(revertMsg("Error: User ID must be greater than zero."));
        id.registerUser(0, "DAVE", "IT");
    }

    function test_DA1_VerifyChain() public {
        verify.addCertificate("CERT-101", "ALICE", "B.TECH COMPUTER SCIENCE", 2027);
        verify.addCertificate("CERT-102", "BOB", "B.TECH COMPUTER SCIENCE", 2027);
        assertEq(verify.getTotalCertificates(), 3, "genesis + 2");
        assertTrue(verify.verifyChainIntegrity(), "valid");
        (string memory name,,,,,) = verify.getCertificate("CERT-101");
        assertEq(name, "ALICE", "lookup works");
    }

    function test_DA1_OnlyAdminAdds() public {
        vm.prank(alice);
        vm.expectRevert(revertMsg("Access Denied: Only admin can perform this operation."));
        verify.addCertificate("CERT-1", "X", "Y", 2027);
    }
}
