#!/usr/bin/env python3
"""Build off-chain certificate metadata and compute IPFS CIDv0 for each file.

The CID is computed locally exactly as `ipfs add --only-hash` would for a small file
(single dag-pb/UnixFS block, sha2-256, base58btc), so it can be pinned later without changing.
No IPFS node is required to run this script.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    pad = len(raw) - len(raw.lstrip(b"\0"))
    return "1" * pad + s


def cid_v0(content: bytes) -> str:
    # UnixFS Data message: Type=File(2), Data=content, filesize=len(content)
    unixfs = b"\x08\x02" + b"\x12" + varint(len(content)) + content + b"\x18" + varint(len(content))
    # dag-pb PBNode: field 1 (Data) = unixfs bytes, no links
    node = b"\x0a" + varint(len(unixfs)) + unixfs
    digest = hashlib.sha256(node).digest()
    return b58encode(b"\x12\x20" + digest)


def main() -> None:
    students = json.loads((ROOT / "data" / "students.json").read_text())
    out_dir = ROOT / "offchain" / "metadata"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for s in students:
        meta = {
            "certId": s["certId"],
            "studentName": s["studentName"],
            "degree": s["degree"],
            "yearOfGraduation": s["yearOfGraduation"],
            "institution": "Vellore Institute of Technology",
            "cgpa": s["cgpa"],
        }
        body = (json.dumps(meta, indent=2, sort_keys=True) + "\n").encode()
        path = out_dir / f"{s['certId']}.json"
        path.write_bytes(body)
        index.append({**s, "ipfsCid": cid_v0(body), "sha256": hashlib.sha256(body).hexdigest()})
    (ROOT / "data" / "certificates_with_cid.json").write_text(json.dumps(index, indent=2) + "\n")
    for row in index:
        print(f"{row['certId']:<10} {row['studentName']:<10} {row['ipfsCid']}")


if __name__ == "__main__":
    main()
