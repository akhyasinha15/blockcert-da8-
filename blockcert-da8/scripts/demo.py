#!/usr/bin/env python3
"""End-to-end demonstration against a local Anvil node (Foundry).

Prerequisites:   anvil --hardfork cancun      (in another terminal)
Run:             python3 scripts/demo.py

Wallet interaction is done with `cast`/`forge` (JSON-RPC over HTTP) using Anvil's public
test accounts. Each step's transcript is saved to docs/transcript/ and gas figures to
docs/gas_report.json.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RPC = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
OUT = ROOT / "docs" / "transcript"
OUT.mkdir(parents=True, exist_ok=True)

# Anvil's well-known development accounts (never use these keys on a real network)
ACCOUNTS = {
    "ADMIN":     ("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"),
    "REGISTRAR": ("0x70997970C51812dc3A010C7d01b50e0d17dc79C8", "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"),
    "STRANGER":  ("0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65", "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"),
}
EVENT_SIGS = [
    "UserRegistered(address,uint256,string,string)",
    "IssuerAuthorized(address)",
    "IssuerRevoked(address)",
    "CertificateIssued(uint256,string,string,address,bytes32,bytes32,string)",
    "CertificateRevoked(string,address,string)",
    "TamperAlert(uint256,string,string)",
]
EVENTS = {}         # topic0 -> event name, resolved locally (no network needed)
ALIAS = {}          # address -> readable name, filled as contracts are deployed
GAS = {}            # operation -> gas used
STEP = [0]
TRANSCRIPT = []


def event_name(topic0: str) -> str:
    if not EVENTS:
        for sig in EVENT_SIGS:
            EVENTS[run(["cast", "keccak", sig]).stdout.strip()] = sig.split("(")[0]
    return EVENTS.get(topic0, topic0)


def pretty(text: str) -> str:
    for addr, name in ALIAS.items():
        text = text.replace(addr, name).replace(addr.lower(), name)
    return text


def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout)
    return p


def begin(title):
    STEP[0] += 1
    TRANSCRIPT.append({"step": STEP[0], "title": title, "lines": []})
    print(f"\n=== Step {STEP[0]}: {title}")


def say(line=""):
    TRANSCRIPT[-1]["lines"].append(line)
    print(line)


def deploy(label, path, ctor_args=(), who="ADMIN"):
    cmd = ["forge", "create", path, "--rpc-url", RPC, "--private-key", ACCOUNTS[who][1], "--broadcast", "--json"]
    if ctor_args:
        cmd += ["--constructor-args", *ctor_args]
    data = json.loads(run(cmd).stdout)
    addr = data["deployedTo"]
    ALIAS[addr] = label
    receipt = json.loads(run(["cast", "receipt", data["transactionHash"], "--json", "--rpc-url", RPC]).stdout)
    GAS[f"deploy {label}"] = int(receipt["gasUsed"], 16) if isinstance(receipt["gasUsed"], str) else receipt["gasUsed"]
    say(f"$ forge create {path}")
    say(f"  Deployed to : {addr}   [{label}]")
    say(f"  Tx hash     : {data['transactionHash']}")
    say(f"  Gas used    : {GAS[f'deploy {label}']}")
    return addr


def send(who, to, sig, *args, gas_key=None, decode_issued=False, expect_revert=False):
    shown = " ".join(f"'{a}'" if " " in str(a) else str(a) for a in args)
    say(f"$ cast send {ALIAS.get(to, to)} '{sig}' {shown}   --from {who}")
    cmd = ["cast", "send", to, sig, *map(str, args), "--rpc-url", RPC, "--private-key", ACCOUNTS[who][1], "--json"]
    p = run(cmd, check=False)
    if p.returncode != 0:
        msg = pretty((p.stderr or p.stdout).strip().splitlines()[-1])
        if "revert" in msg:
            reason = msg.split("execution reverted:")[-1].split(", data:")[0].strip()
            say(f"  status      : REVERTED")
            say(f"  reason      : {reason}")
            if not expect_revert:
                raise RuntimeError(msg)
            return None
        raise RuntimeError(msg)
    r = json.loads(p.stdout)
    gas = int(r["gasUsed"], 16) if isinstance(r["gasUsed"], str) else r["gasUsed"]
    blk = int(r["blockNumber"], 16) if isinstance(r["blockNumber"], str) else r["blockNumber"]
    if gas_key:
        GAS[gas_key] = gas
    say(f"  status      : {'SUCCESS' if r['status'] in ('0x1', 1, '0x01') else 'FAILED'}")
    say(f"  block       : {blk}")
    say(f"  tx hash     : {r['transactionHash']}")
    say(f"  gas used    : {gas}")
    for log in r["logs"]:
        name = event_name(log["topics"][0])
        say(f"  event       : {name}")
        if decode_issued and name.startswith("CertificateIssued"):
            dec = run(["cast", "abi-decode", "f()(string,string,bytes32,bytes32,string)", log["data"]]).stdout.split("\n")
            say(f"      index        = {int(log['topics'][1], 16)}")
            say(f"      certId       = {dec[0]}")
            say(f"      studentName  = {dec[1]}")
            say(f"      blockHash    = {dec[2]}")
            say(f"      previousHash = {dec[3]}")
            say(f"      ipfsCid      = {dec[4]}")
    return r


def call(to, sig, *args, ret=None):
    shown = " ".join(f"'{a}'" if " " in str(a) else str(a) for a in args)
    say(f"$ cast call {ALIAS.get(to, to)} '{sig}' {shown}")
    full = f"{sig}({ret})" if ret else sig
    out = run(["cast", "call", to, full, *map(str, args), "--rpc-url", RPC]).stdout.strip()
    for line in pretty(out).splitlines():
        say(f"  {line}")
    return out


def main():
    certs = json.loads((ROOT / "data" / "certificates_with_cid.json").read_text())
    block = "(string,string,string,uint16,string,address,bytes32,bytes32,uint64,bool)"
    ret_check = "bool,bool,address"

    for k, (a, _) in ACCOUNTS.items():
        ALIAS[a] = k

    begin("Deploy DigitalIdentity (DA-1 Q2) and CertificateRegistry (DA-8)")
    ident = deploy("DigitalIdentity", "src/DigitalIdentity.sol:DigitalIdentity")
    reg = deploy("CertificateRegistry", "src/CertificateRegistry.sol:CertificateRegistry", [ident])
    say(f"$ cast call CertificateRegistry 'totalBlocks()(uint256)'")
    say("  " + run(["cast", "call", reg, "totalBlocks()(uint256)", "--rpc-url", RPC]).stdout.strip() + "   <- genesis block only")

    begin("Identity layer: register the university registrar wallet")
    send("REGISTRAR", ident, "registerUser(uint256,string,string)", 1, "Registrar Office", "Academic Affairs",
         gas_key="registerUser")
    call(ident, "isWalletRegistered(address)(bool)", ACCOUNTS["REGISTRAR"][0])
    call(ident, "isWalletRegistered(address)(bool)", ACCOUNTS["STRANGER"][0])

    begin("Access control: authorise issuers (identity check enforced)")
    send("ADMIN", reg, "authorizeIssuer(address)", ACCOUNTS["STRANGER"][0], expect_revert=True)
    send("ADMIN", reg, "authorizeIssuer(address)", ACCOUNTS["REGISTRAR"][0], gas_key="authorizeIssuer")
    send("STRANGER", reg, "issueCertificate(string,string,string,uint16,string)",
         "CERT-999", "MALLORY", "B.TECH", 2027, "QmFake", expect_revert=True)

    begin("Issue certificates (each becomes a hash-linked block)")
    for i, c in enumerate(certs[:3]):
        send("REGISTRAR", reg, "issueCertificate(string,string,string,uint16,string)",
             c["certId"], c["studentName"], c["degree"], c["yearOfGraduation"], c["ipfsCid"],
             gas_key=f"issueCertificate #{i+1}", decode_issued=(i < 2))
        if i == 0:
            say("")
    send("REGISTRAR", reg, "issueCertificate(string,string,string,uint16,string)",
         certs[0]["certId"], "MALLORY", certs[0]["degree"], certs[0]["yearOfGraduation"], "QmDup", expect_revert=True)

    begin("Read the chain and verify certificates")
    call(reg, "totalBlocks()(uint256)")
    call(reg, "getCertificate(string)", certs[1]["certId"], ret=block)
    call(reg, "verifyCertificate(string,string,string,uint16)", "CERT-102", "BOB", "B.TECH COMPUTER SCIENCE", 2027,
         ret=ret_check)
    say("  ^ authentic=true, revoked=false, issuer=REGISTRAR")
    call(reg, "verifyCertificate(string,string,string,uint16)", "CERT-102", "BOB", "B.TECH COMPUTER SCIENCE", 2030,
         ret=ret_check)
    say("  ^ forged graduation year -> authentic=false")
    call(reg, "verifyChainIntegrity()", ret="bool,uint256")

    begin("Revoke a certificate (history preserved, chain still valid)")
    send("REGISTRAR", reg, "revokeCertificate(string,string)", "CERT-103", "Degree withdrawn by academic council",
         gas_key="revokeCertificate")
    call(reg, "verifyCertificate(string,string,string,uint16)", "CERT-103", "CHARLIE", "B.TECH CYBER SECURITY", 2027,
         ret=ret_check)
    say("  ^ authentic=true (record intact), revoked=true")
    call(reg, "verifyChainIntegrity()", ret="bool,uint256")

    begin("Tamper detection on a corrupted copy of the registry (test harness)")
    h = deploy("RegistryHarness", "test/mocks/RegistryHarness.sol:RegistryHarness", [ident])
    send("ADMIN", h, "authorizeIssuer(address)", ACCOUNTS["REGISTRAR"][0])
    for c in certs[:3]:
        send("REGISTRAR", h, "issueCertificate(string,string,string,uint16,string)",
             c["certId"], c["studentName"], c["degree"], c["yearOfGraduation"], c["ipfsCid"])
    call(h, "verifyChainIntegrity()", ret="bool,uint256")
    say("  ^ chain intact before the attack")
    say("")
    say("# attacker silently edits block 2 (BOB -> MALLORY) directly in storage")
    send("ADMIN", h, "corruptStudentName(uint256,string)", 2, "MALLORY")
    call(h, "verifyChainIntegrity()", ret="bool,uint256")
    say("  ^ valid=false, firstBadIndex=2  -> blockchain compromised")
    r = send("ADMIN", h, "auditChain()", gas_key="auditChain (tampered)")
    if r:
        for log in r["logs"]:
            dec = run(["cast", "abi-decode", "f()(string,string)", log["data"]]).stdout.split("\n")
            say(f"      TamperAlert(index={int(log['topics'][1], 16)}, certId={dec[0]})")
            say(f"      message = {dec[1]}")

    (OUT / "transcript.json").write_text(json.dumps(TRANSCRIPT, indent=2))
    for t in TRANSCRIPT:
        (OUT / f"step_{t['step']:02d}.txt").write_text(f"# Step {t['step']}: {t['title']}\n" + "\n".join(t["lines"]) + "\n")
    (ROOT / "docs" / "gas_report.json").write_text(json.dumps(GAS, indent=2))
    print("\nSaved transcript and gas report under docs/")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        sys.exit(f"demo failed: {e}")
