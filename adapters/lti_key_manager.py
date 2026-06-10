import json
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwcrypto import jwk

from config.lti_settings import LTISettings


class LtiKeyManager:
    def __init__(self, settings: LTISettings | None = None):
        self.settings = settings or LTISettings()
        self._ensure_keys()

    def _ensure_keys(self):
        os.makedirs(self.settings.keys_dir, exist_ok=True)
        private_path = os.path.join(self.settings.keys_dir, "private.key")
        public_path = os.path.join(self.settings.keys_dir, "public.key")

        if not os.path.exists(private_path):
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            with open(private_path, "wb") as f:
                f.write(
                    key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
            with open(public_path, "wb") as f:
                f.write(
                    key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                )

    def get_private_key_pem(self) -> str:
        private_path = os.path.join(self.settings.keys_dir, "private.key")
        with open(private_path) as f:
            return f.read()

    def get_public_key_pem(self) -> str:
        public_path = os.path.join(self.settings.keys_dir, "public.key")
        with open(public_path) as f:
            return f.read()

    def get_jwks(self) -> dict:
        public_key_pem = self.get_public_key_pem()
        key = jwk.JWK.from_pem(public_key_pem.encode("utf-8"))
        key_dict = json.loads(key.export_public())

        return {"keys": [
            {
                "kty": key_dict.get("kty", "RSA"),
                "use": "sig",
                "alg": "RS256",
                "kid": key_dict.get("kid", "echo-key-1"),
                "n": key_dict.get("n"),
                "e": key_dict.get("e"),
            }
        ]}
