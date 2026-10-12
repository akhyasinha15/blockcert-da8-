// Ethers.js v6 client for CertificateRegistry (DA-8).
//
//   cd scripts/ethers && npm install
//   REGISTRY=0x... PRIVATE_KEY=0x... node client.mjs verify CERT-102 BOB "B.TECH COMPUTER SCIENCE" 2027
//   REGISTRY=0x... PRIVATE_KEY=0x... node client.mjs issue  CERT-107 GRACE "B.TECH IT" 2027 QmSomeCid
//   REGISTRY=0x... node client.mjs integrity
//
// Defaults to a local Anvil/Hardhat node; set RPC_URL for a testnet. In a browser dApp,
// replace JsonRpcProvider/Wallet with `new BrowserProvider(window.ethereum)` + `getSigner()`
// so MetaMask signs the transactions.
import { JsonRpcProvider, Wallet, Contract } from "ethers";

const ABI = [
  "function issueCertificate(string certId, string studentName, string degree, uint16 year, string ipfsCid) returns (bytes32)",
  "function revokeCertificate(string certId, string reason)",
  "function verifyCertificate(string certId, string studentName, string degree, uint16 year) view returns (bool authentic, bool revoked, address issuer)",
  "function verifyChainIntegrity() view returns (bool valid, uint256 badIndex)",
  "function totalBlocks() view returns (uint256)",
  "event CertificateIssued(uint256 indexed index, string certId, string studentName, address indexed issuer, bytes32 blockHash, bytes32 previousHash, string ipfsCid)",
  "event TamperAlert(uint256 indexed index, string certId, string message)",
];

const { RPC_URL = "http://127.0.0.1:8545", REGISTRY, PRIVATE_KEY } = process.env;
if (!REGISTRY) throw new Error("Set REGISTRY to the deployed CertificateRegistry address");

const provider = new JsonRpcProvider(RPC_URL);
const signer = PRIVATE_KEY ? new Wallet(PRIVATE_KEY, provider) : provider;
const registry = new Contract(REGISTRY, ABI, signer);

const [cmd, ...a] = process.argv.slice(2);

if (cmd === "issue") {
  const [id, name, degree, year, cid] = a;
  const tx = await registry.issueCertificate(id, name, degree, Number(year), cid);
  const receipt = await tx.wait();
  console.log("issued in block", receipt.blockNumber, "tx", tx.hash, "gas", receipt.gasUsed.toString());
} else if (cmd === "verify") {
  const [id, name, degree, year] = a;
  const [authentic, revoked, issuer] = await registry.verifyCertificate(id, name, degree, Number(year));
  console.log({ authentic, revoked, issuer });
} else if (cmd === "integrity") {
  const [valid, badIndex] = await registry.verifyChainIntegrity();
  console.log(valid ? "Chain intact" : `Blockchain compromised at block ${badIndex}`);
} else {
  console.log("usage: client.mjs issue|verify|integrity ...");
}
