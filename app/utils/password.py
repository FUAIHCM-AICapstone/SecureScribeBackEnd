import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() + salt


def verify_password(password: str, hashed_password: str) -> bool:
    salt = hashed_password[-32:]
    return (
        hashlib.sha256(f"{salt}{password}".encode()).hexdigest() + salt
        == hashed_password
    )
