"""Published reference checksums for standard chunks.

Each entry is the SHA-256 of a chunk in PiScope's storage encoding (one byte per digit,
values 0-9) computed from a *published* digit file, not from this project's generator.
Shipping it lets every build, including offline Docker and CI builds, check the first
chunk against an external source.

Provenance of chunk 0 (decimal positions 1 to 1,000,000), retrieved 2026-11-16:

* https://pi2e.ch/blog/wp-content/uploads/2017/03/pi_dec_1m.txt
  (file SHA-256 dd382ef6a0c1e8d920fb72f482d74826251ab97709520bc24f913cd8eb5fc839)
* https://www.angio.net/pi/digits/pi1000000.txt
  (file SHA-256 b50ea720602439dcb8a56265b75fadfa4d0a0fbd46d9705693dde14b8a053fb0)

Both files contain identical digits.
"""

REFERENCE_CHUNK_SIZE = 1_000_000

REFERENCE_CHUNK_SHA256: dict[int, str] = {
    0: "344b0f42bd832f29a22d6b829af80e325c4fac22d88a1efb5e21b7a3632c1086",
}

REFERENCE_SOURCE = (
    "published first million decimals of pi (pi2e.ch and angio.net copies, identical), "
    "retrieved 2026-11-16"
)
