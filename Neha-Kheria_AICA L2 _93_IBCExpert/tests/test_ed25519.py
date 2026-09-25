from app.security import ed25519


def test_rfc8032_vector_1_and_tampering():
    seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    public_expected = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    signature_expected = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    public = ed25519.publickey_from_seed(seed)
    signature = ed25519.sign(seed, b"")
    assert public == public_expected
    assert signature == signature_expected
    assert ed25519.verify(public, b"", signature)
    assert not ed25519.verify(public, b"changed", signature)
    assert not ed25519.verify(public, b"", bytes([signature[0] ^ 1]) + signature[1:])


def test_rfc8032_vector_2():
    seed = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    public_expected = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    message = bytes.fromhex("72")
    signature_expected = bytes.fromhex(
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
    )
    public = ed25519.publickey_from_seed(seed)
    signature = ed25519.sign(seed, message)
    assert public == public_expected
    assert signature == signature_expected
    assert ed25519.verify(public, message, signature)
