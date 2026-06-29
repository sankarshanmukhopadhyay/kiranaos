import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.domain import Operator, OperatorRole, Store
from app.schemas.domain import OperatorCreateIn

bearer = HTTPBearer(auto_error=False)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), get_settings().password_pbkdf2_iterations)
    return f"pbkdf2_sha256${get_settings().password_pbkdf2_iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if len(parts) == 3:  # backward-compatible verifier for v2.1.0 hashes
            algorithm, salt, digest = parts
            iterations = 120_000
        else:
            algorithm, iterations_raw, salt, digest = parts
            iterations = int(iterations_raw)
    except (ValueError, TypeError):
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(candidate, digest)


def create_access_token(operator: Operator) -> str:
    settings = get_settings()
    header = {"alg": "HS256", "typ": "JWT"}
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {
        "sub": str(operator.id),
        "store_id": operator.store_id,
        "role": str(operator.role),
        "exp": int(exp.timestamp()),
    }
    signing_input = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
        header = json.loads(_unb64(header_b64))
        payload = json.loads(_unb64(payload_b64))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise HTTPException(status_code=401, detail="Invalid token header")

    signing_input = f"{header_b64}.{payload_b64}"
    expected = hmac.new(settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64(expected), signature_b64):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=401, detail="Token expired")
    if not payload.get("sub") or not payload.get("store_id") or not payload.get("role"):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    return payload


def ensure_default_store(db: Session) -> Store:
    store = db.get(Store, get_settings().default_store_id)
    if store:
        return store
    store = Store(id=get_settings().default_store_id, name="Main Store", slug="main")
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def create_operator(db: Session, payload: OperatorCreateIn) -> Operator:
    ensure_default_store(db)
    existing = db.scalar(
        select(Operator).where(
            Operator.store_id == payload.store_id,
            Operator.username == payload.username,
        )
    )
    if existing:
        raise ValueError("Operator username already exists for this store")
    operator = Operator(
        store_id=payload.store_id,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


def authenticate_operator(db: Session, username: str, password: str, store_id: int) -> Operator:
    operator = db.scalar(
        select(Operator).where(Operator.store_id == store_id, Operator.username == username)
    )
    if not operator or not verify_password(password, operator.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return operator


def operator_count(db: Session) -> int:
    return int(db.scalar(select(func.count(Operator.id))) or 0)


def current_operator(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Operator | None:
    settings = get_settings()
    ensure_default_store(db)
    if not settings.auth_required:
        return None
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    operator = db.get(Operator, int(payload["sub"]))
    if not operator or operator.store_id != int(payload["store_id"]):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return operator


def current_store_id(
    db: Session = Depends(get_db),
    operator: Operator | None = Depends(current_operator),
) -> int:
    ensure_default_store(db)
    if operator is None:
        return get_settings().default_store_id
    return int(operator.store_id)



def require_roles(*allowed: OperatorRole):
    def _dependency(operator: Operator | None = Depends(current_operator)) -> Operator | None:
        if operator is None:
            return None
        if operator.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient operator role")
        return operator
    return _dependency
