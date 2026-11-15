# Test fixtures

`pi_first_10000_decimals.txt` holds the first 10,000 decimal digits of pi (positions
1 to 10,000, no leading `3.`). It was cut from a published file, not produced by this
project's generator, so tests that compare against it are an independent check:

- Source: https://pi2e.ch/blog/wp-content/uploads/2017/03/pi_dec_1m.txt
- Retrieved: 2026-11-16
- Source file SHA-256: `dd382ef6a0c1e8d920fb72f482d74826251ab97709520bc24f913cd8eb5fc839`

The full one million digits of that file also matched a second published copy
(https://www.angio.net/pi/digits/pi1000000.txt, SHA-256
`b50ea720602439dcb8a56265b75fadfa4d0a0fbd46d9705693dde14b8a053fb0`) digit for digit.

`REFERENCE_FIRST_MILLION_SHA256` in `tests/conftest.py` is the SHA-256 of the first
1,000,000 decimals of the pi2e.ch file in PiScope's storage encoding (one byte per
digit, values 0-9).
