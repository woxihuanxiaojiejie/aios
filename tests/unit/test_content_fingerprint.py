from __future__ import annotations


def test_content_fingerprint_normalizes_unicode_and_whitespace() -> None:
    from aios.integrations.fingerprint import content_fingerprint

    composed = "Caf\u00e9\nprices\t fell"
    decomposed = "Cafe\u0301 prices  fell"

    assert content_fingerprint(composed) == content_fingerprint(decomposed)


def test_content_fingerprint_preserves_case_digits_and_punctuation() -> None:
    from aios.integrations.fingerprint import content_fingerprint

    assert content_fingerprint("Buy 10 shares.") != content_fingerprint(
        "buy 10 shares."
    )
    assert content_fingerprint("Buy 10 shares.") != content_fingerprint(
        "Buy 11 shares."
    )
    assert content_fingerprint("Buy 10 shares.") != content_fingerprint(
        "Buy 10 shares!"
    )


def test_content_fingerprint_is_sha256_hex() -> None:
    from aios.integrations.fingerprint import content_fingerprint

    digest = content_fingerprint("same content")

    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)
