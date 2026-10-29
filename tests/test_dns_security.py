"""Bounded regression for GHSA-45c3-73f7-pv4m's DNS pointer-chain limit."""

import dns.name
import pytest


def compressed_root_chain(hops: int) -> tuple[bytes, int]:
    wire = bytearray(b"\x00")
    offset = 0
    for _ in range(hops):
        previous = offset
        offset = len(wire)
        wire.extend((0xC000 | previous).to_bytes(2, "big"))
    return bytes(wire), offset


def test_dns_accepts_sixteen_backward_compression_pointers():
    wire, offset = compressed_root_chain(16)
    assert len(wire) == 33
    assert dns.name.from_wire(wire, offset) == (dns.name.root, 2)


def test_dns_rejects_seventeen_backward_compression_pointers():
    # The unfixed parser accepts this 35-byte chain; no large payload or DNS I/O.
    wire, offset = compressed_root_chain(17)
    assert len(wire) == 35
    with pytest.raises(dns.name.PointerChainTooLong):
        dns.name.from_wire(wire, offset)
