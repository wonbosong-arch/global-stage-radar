"""Encrypted P1 history handoff. Only ciphertext may leave the runner.

RSA-OAEP wraps a fresh AES-GCM key. No credentials, response bodies, exception
messages or request headers enter the payload. Decryption is local and read-only.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CONTEXT = b"global-stage-radar/p1-history-review/v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def public_key(raw):
    key = serialization.load_pem_public_key(raw)
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 3072:
        raise ValueError("A review RSA public key of at least 3072 bits is required")
    return key


def seal(payload, recipient):
    key = public_key(recipient)
    secret, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
    wrapped = key.encrypt(secret, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                             algorithm=hashes.SHA256(), label=CONTEXT))
    encrypted = AESGCM(secret).encrypt(nonce, canonical(payload), CONTEXT)
    return canonical({"schema_version": 1, "wrapped_key": base64.b64encode(wrapped).decode(),
                      "nonce": base64.b64encode(nonce).decode(),
                      "ciphertext": base64.b64encode(encrypted).decode()})


def unseal(raw, private_key):
    envelope = json.loads(raw)
    if envelope["schema_version"] != 1:
        raise ValueError("Unsupported encrypted bundle")
    key = serialization.load_pem_private_key(private_key, password=None)
    wrapped, nonce, encrypted = (base64.b64decode(envelope[k], validate=True)
                                  for k in ("wrapped_key", "nonce", "ciphertext"))
    secret = key.decrypt(wrapped, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                             algorithm=hashes.SHA256(), label=CONTEXT))
    return json.loads(AESGCM(secret).decrypt(nonce, encrypted, CONTEXT))


def save_encrypted(path: Path, payload, recipient):
    """No overwrite, no plaintext intermediate; output must be outside checkouts."""
    from nasdaq_single_source import private_path
    target = private_path(path, existing=False)
    encrypted = seal(payload, recipient)
    with target.open("xb") as stream:
        stream.write(encrypted)
