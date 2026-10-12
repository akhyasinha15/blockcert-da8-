#!/usr/bin/env python3
"""Draw the architecture, hash-chain and sequence diagrams used in the DA-8 report."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
NAVY, BLUE, TEAL, AMBER, RED, GREY, LIGHT = "#2c3e70", "#3b82c4", "#1f9d8b", "#e0a030", "#d64545", "#6b7280", "#eef2fa"


def box(ax, x, y, w, h, text, fc=LIGHT, ec=NAVY, fs=8.5, bold=False, tc="#111", lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(ax, p1, p2, text=None, color=NAVY, rad=0.0, fs=7, off=(0, 0.08), ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=11, color=color, lw=1.3,
                                 connectionstyle=f"arc3,rad={rad}", linestyle=ls))
    if text:
        ax.text((p1[0] + p2[0]) / 2 + off[0], (p1[1] + p2[1]) / 2 + off[1], text, ha="center", va="center",
                fontsize=fs, color=color, backgroundcolor="white")


def canvas(w, h, xl, yl):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xl); ax.set_ylim(0, yl); ax.axis("off")
    return fig, ax


def architecture():
    fig, ax = canvas(7.2, 5.3, 12, 9.0)
    ax.text(6, 8.75, "Figure 1 - System architecture and module integration", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    ax.text(0.2, 8.25, "CLIENT / WALLET LAYER", fontsize=7.5, color=GREY, fontweight="bold")
    box(ax, 0.3, 7.2, 3.4, 0.85, "Remix IDE + Remix VM\n(DA-1 manual testing)", fc="#fff7e6", ec=AMBER, fs=8)
    box(ax, 4.3, 7.2, 3.4, 0.85, "cast / forge (JSON-RPC)\nscripts/demo.py", fc="#fff7e6", ec=AMBER, fs=8)
    box(ax, 8.3, 7.2, 3.4, 0.85, "Ethers.js v6 client\nscripts/ethers/client.mjs", fc="#fff7e6", ec=AMBER, fs=8)
    box(ax, 0.3, 6.0, 11.4, 0.65, "EVM node: Anvil local chain (Cancun, chain-id 31337)  -  signed transactions / eth_call", fc="#e8f6f3", ec=TEAL, fs=8)
    for x in (2.0, 6.0, 10.0):
        arrow(ax, (x, 7.2), (x, 6.65), color=AMBER)
    ax.text(0.2, 5.55, "ON-CHAIN SMART CONTRACTS", fontsize=7.5, color=GREY, fontweight="bold")
    box(ax, 0.3, 2.55, 3.2, 2.7, "DigitalIdentity.sol\n(DA-1 Q2)\n\nregisterUser()\ngetUser()\nisWalletRegistered()", fc=LIGHT, fs=7.8)
    box(ax, 4.6, 2.55, 3.9, 2.7, "CertificateRegistry.sol (DA-8)\n\nauthorizeIssuer()  [onlyAdmin]\nissueCertificate()  [onlyIssuer]\nrevokeCertificate()\nverifyCertificate()\nverifyChainIntegrity() / auditChain()", fc="#e9f0fb", ec=BLUE, lw=2, fs=7.8)
    box(ax, 9.3, 2.55, 2.4, 2.7, "Verify.sol\n(DA-1 Q1)\n\nlegacy hash chain\nkept for regression\ntests", fc="#f3f4f6", ec=GREY, fs=7.8)
    arrow(ax, (4.6, 3.9), (3.5, 3.9), color=TEAL)
    ax.text(4.05, 4.25, "identity\ncheck", ha="center", fontsize=6.3, color=TEAL)
    for x, ls in ((1.9, "-"), (6.55, "-"), (10.5, "--")):
        arrow(ax, (x, 6.0), (x, 5.25), color=TEAL, ls=ls)
    ax.text(0.2, 2.05, "OFF-CHAIN STORAGE", fontsize=7.5, color=GREY, fontweight="bold")
    box(ax, 0.3, 0.2, 3.4, 1.0, "data/students.json\n(source dataset)", fc="#f3f4f6", ec=GREY, fs=8)
    box(ax, 4.4, 0.2, 3.5, 1.0, "offchain/metadata/*.json\n(content-addressed, CIDv0)", fc="#f3f4f6", ec=GREY, fs=8)
    box(ax, 8.6, 0.2, 3.1, 1.0, "IPFS network\n(pin by CID)", fc="#f3f4f6", ec=GREY, fs=8)
    arrow(ax, (3.7, 0.7), (4.4, 0.7), color=GREY)
    arrow(ax, (7.9, 0.7), (8.6, 0.7), color=GREY, ls="--")
    arrow(ax, (6.15, 1.2), (6.15, 2.55), color=BLUE)
    ax.text(6.35, 1.9, "ipfsCid stored on-chain", fontsize=6.5, color=BLUE, va="center")
    fig.savefig(OUT / "diagram_architecture.png", dpi=220, bbox_inches="tight"); plt.close(fig)


def chain():
    fig, ax = canvas(7.2, 3.6, 12, 6.0)
    ax.text(6, 5.75, "Figure 2 - Hash-linked certificate blocks (values from the live demo)", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    blocks = [
        ("Block 0  GENESIS", ["id: GENESIS", "prev: 0x0000...", "hash: 0x8229fdb3..."], "#f3f4f6", GREY),
        ("Block 1  CERT-101", ["student: ALICE", "prev: 0x8229fdb3...", "hash: 0x0fec4ce8..."], LIGHT, NAVY),
        ("Block 2  CERT-102", ["student: BOB", "prev: 0x0fec4ce8...", "hash: 0x566454e7..."], LIGHT, NAVY),
        ("Block 3  CERT-103", ["student: CHARLIE", "prev: 0x566454e7...", "hash: keccak256(...)"], LIGHT, NAVY),
    ]
    x, w, gap = 0.3, 2.4, 0.55
    for i, (t, lines, fc, ec) in enumerate(blocks):
        ax.add_patch(FancyBboxPatch((x, 3.0), w, 2.1, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.4))
        ax.text(x + w / 2, 4.8, t, ha="center", fontsize=7.8, fontweight="bold", color=ec)
        for j, l in enumerate(lines):
            ax.text(x + 0.12, 4.25 - j * 0.42, l, fontsize=6.2, color="#222", family="monospace")
        ax.text(x + 0.12, 3.1, "+ issuer, ipfsCid, time", fontsize=5.6, color=GREY)
        if i:
            arrow(ax, (x - gap + 0.02, 3.55), (x - 0.02, 3.55), color=BLUE)
        x += w + gap
    ax.text(6, 2.55, "hash = keccak256( abi.encode(certId, studentName, degree, year, ipfsCid, previousHash) )",
            ha="center", fontsize=6.8, family="monospace", color=NAVY)
    ax.add_patch(FancyBboxPatch((1.0, 0.1), 10.0, 1.7, boxstyle="round,pad=0.02,rounding_size=0.08", fc="#fdecec", ec=RED, lw=1.4))
    ax.text(6, 1.5, "Tamper case: Block 2 student BOB changed to MALLORY", ha="center", fontsize=7.8, fontweight="bold", color=RED)
    ax.text(6, 1.05, "recomputed hash != stored hash at Block 2", ha="center", fontsize=6.8, color="#333", family="monospace")
    ax.text(6, 0.55, "verifyChainIntegrity() -> (false, 2) ; auditChain() emits TamperAlert", ha="center", fontsize=6.8, color="#333", family="monospace")
    arrow(ax, (6.3, 2.35), (6.3, 1.85), color=RED, ls="--")
    fig.savefig(OUT / "diagram_chain.png", dpi=220, bbox_inches="tight"); plt.close(fig)


def sequence():
    fig, ax = canvas(7.2, 4.4, 12, 7.4)
    ax.text(6, 7.15, "Figure 3 - Issuance and verification sequence", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    actors = [("Admin\n(wallet)", 1.0), ("Registrar\n(wallet)", 3.3), ("Digital\nIdentity", 5.7), ("Certificate\nRegistry", 8.4), ("Employer\n(any client)", 10.8)]
    for name, x in actors:
        box(ax, x - 0.95, 6.1, 1.9, 0.8, name, fc=LIGHT, fs=7.5, bold=True)
        ax.plot([x, x], [6.1, 0.2], color="#c3cad8", lw=1, ls="--")
    def msg(i, j, y, text, color=NAVY, ret=False):
        xi, xj = actors[i][1], actors[j][1]
        arrow(ax, (xi, y), (xj, y), color=color, ls="--" if ret else "-")
        ax.text((xi + xj) / 2, y + 0.16, text, ha="center", fontsize=6.4, color=color)
    msg(1, 2, 5.7, "1  registerUser(1, 'Registrar Office', ...)")
    msg(0, 3, 5.15, "2  authorizeIssuer(registrar)")
    msg(3, 2, 4.7, "3  isWalletRegistered(registrar)?", color=TEAL)
    msg(2, 3, 4.25, "true", color=TEAL, ret=True)
    msg(1, 3, 3.7, "4  issueCertificate(id, name, degree, year, cid)")
    ax.text(8.4, 3.2, "onlyIssuer -> hash(data, prevHash) -> push block\nemit CertificateIssued", ha="center", fontsize=6.0, color=GREY)
    msg(4, 3, 2.45, "5  verifyCertificate(id, name, degree, year)", color=BLUE)
    msg(3, 4, 2.0, "(authentic, revoked, issuer)", color=BLUE, ret=True)
    msg(4, 3, 1.45, "6  verifyChainIntegrity()", color=BLUE)
    msg(3, 4, 1.0, "(valid, badIndex)", color=BLUE, ret=True)
    fig.savefig(OUT / "diagram_sequence.png", dpi=220, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    architecture(); chain(); sequence()
    print("diagrams written to", OUT)
