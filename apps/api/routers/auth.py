"""
Authentication router - Keycloak integration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import logging

from models.database import get_db, User
from config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logger = logging.getLogger(__name__)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency: Get current authenticated user from JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT (Keycloak public key)
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.KEYCLOAK_CLIENT_ID
        )

        keycloak_user_id: str = payload.get("sub")
        if keycloak_user_id is None:
            raise credentials_exception

    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(
        select(User).where(User.keycloak_user_id == keycloak_user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # User doesn't exist in our DB - create from Keycloak data
        email = payload.get("email")
        name = payload.get("name")

        user = User(
            email=email,
            name=name,
            keycloak_user_id=keycloak_user_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user created from Keycloak: {email}")

    return user


@router.post("/exchange-token")
async def exchange_keycloak_token(
    code: str,
    redirect_uri: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange Keycloak authorization code for access token
    Called by frontend after OAuth redirect
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(400, "Token exchange failed")

            return response.json()

        except httpx.RequestError as e:
            logger.error(f"Keycloak request error: {e}")
            raise HTTPException(500, "Authentication service unavailable")


@router.post("/refresh-token")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                    "refresh_token": refresh_token
                }
            )

            if response.status_code != 200:
                raise HTTPException(400, "Token refresh failed")

            return response.json()

        except httpx.RequestError as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(500, "Authentication service unavailable")


@router.post("/logout")
async def logout(refresh_token: str):
    """
    Logout user (revoke tokens)
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/logout",
                data={
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                    "refresh_token": refresh_token
                }
            )

            if response.status_code != 204:
                logger.warning(f"Logout response: {response.status_code}")

            return {"status": "logged_out"}

        except httpx.RequestError as e:
            logger.error(f"Logout error: {e}")
            raise HTTPException(500, "Logout failed")
