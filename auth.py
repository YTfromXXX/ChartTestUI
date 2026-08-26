"""JWT authentication for the observer API."""

from datetime import datetime, timedelta, timezone
import os

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


def _secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    return secret


def authenticate_user(email: str, password: str) -> bool:
    configured_email = os.getenv("AUTH_EMAIL", "observer@example.com").strip().lower()
    configured_hash = os.getenv("AUTH_PASSWORD_HASH")
    if not configured_hash:
        raise RuntimeError("AUTH_PASSWORD_HASH must be configured")
    try:
        password_matches = bcrypt.checkpw(password.encode(), configured_hash.encode())
    except ValueError:
        password_matches = False
    return email.strip().lower() == configured_email and password_matches


def issue_token(email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)
    return jwt.encode({"sub": email.strip().lower(), "exp": expires}, _secret(), algorithm="HS256")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise credentials_error
        return subject
    except (JWTError, RuntimeError) as error:
        raise credentials_error from error


def token_form() -> type[OAuth2PasswordRequestForm]:
    return OAuth2PasswordRequestForm