# BlockCert - Blockchain Digital Certificate & Identity System

**BCSE329P - Blockchain and Distributed Ledger Technology Lab - DA-8 (Report-2)**
Akhya Sinha - 23BKT0045 - VIT Vellore

An integrated Solidity system that builds on the two DA-1 contracts:

| Module | File | Origin |
|---|---|---|
| Wallet identity registry | `src/DigitalIdentity.sol` | DA-1 Q2 (unchanged) |
| Legacy hash-chain certificate contract | `src/Verify.sol` | DA-1 Q1 (unchanged) |
| **Integrated certificate registry** | `src/CertificateRegistry.sol` | **new in DA-8** |
| Tamper-simulation harness (tests only) | `test/mocks/RegistryHarness.sol` | new in DA-8 |

`CertificateRegistry` adds: issuer roles gated by `DigitalIdentity`, IPFS CID references for off-chain
documents, revocation, `abi.encode` hashing, certificate verification against claimed details, and
chain-wide tamper auditing (`verifyChainIntegrity`, `auditChain` -> `TamperAlert`).

## Repository layout

```
src/                  Solidity contracts
test/                 Foundry tests (21) - no external dependencies, forge-std not required
scripts/demo.py       End-to-end demo against a local Anvil node (writes docs/transcript/)
scripts/make_metadata.py   Builds off-chain metadata JSON + IPFS CIDv0 from data/students.json
scripts/ethers/       Ethers.js v6 client (issue / verify / integrity)
data/                 Dataset (students.json, certificates_with_cid.json)
offchain/metadata/    Certificate metadata files (the content that would be pinned to IPFS)
docs/                 Report figures, captured transcripts, gas report
```

## Quick start (Foundry)

```bash
curl -L https://foundry.paradigm.xyz | bash && foundryup     # install forge / anvil / cast
forge test -vv                                               # 21 tests
anvil --hardfork cancun                                      # terminal 1
python3 scripts/make_metadata.py && python3 scripts/demo.py  # terminal 2
```

## Quick start (Remix IDE - same environment as DA-1)

1. Open https://remix.ethereum.org and copy `src/DigitalIdentity.sol` and `src/CertificateRegistry.sol` into the workspace.
2. Compile with Solidity 0.8.20+ (EVM version: cancun).
3. Deploy `DigitalIdentity`, then deploy `CertificateRegistry` passing the `DigitalIdentity` address.
4. From account 2: `registerUser(1,"Registrar Office","Academic Affairs")`; from account 1 (admin): `authorizeIssuer(<account 2>)`.
5. From account 2: `issueCertificate("CERT-101","ALICE","B.TECH COMPUTER SCIENCE",2027,"<cid from data/certificates_with_cid.json>")`.

## Ethers.js client

```bash
cd scripts/ethers && npm install
REGISTRY=<address> RPC_URL=http://127.0.0.1:8545 node client.mjs integrity
```

## Notes

* Anvil's private keys in `scripts/demo.py` are the public development keys - never use them on a real network.
* IPFS CIDs are computed locally in exactly the way `ipfs add --only-hash` would; pin the files in
  `offchain/metadata/` to an IPFS node/service to make them retrievable.
* On-chain storage is append-only, so tampering is simulated with `RegistryHarness`, which writes
  directly to storage to model a corrupted node.

## Licence

MIT
