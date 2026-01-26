from functools import lru_cache
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from app.core.config import settings
from app.models.dto.auth import TokenPayload
import logging
import requests

logger = logging.getLogger(__name__)

@lru_cache
def get_jwks():
    response = requests.get(settings.SUPABASE_JWT_URL)
    response.raise_for_status()
    return response.json()


class JWTValidator:
    
    @staticmethod
    def verify_token(token: str) -> TokenPayload:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            # Decode JWT using Supabase JWT secret
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise InvalidTokenError("Missing kid in token header")
            
            jwks = get_jwks()
            key = next(
                (k for k in jwks["keys"] if k["kid"] == kid),
                None
            )
            
            if not key:
                raise InvalidTokenError("No matching key found in JWKS")
            
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.ALGORITHM],
                audience=settings.SUPABASE_AUDIENCE,
                issuer=f"{settings.SUPABASE_URL}/auth/v1"
            )
            
            token_data = TokenPayload(
                sub=payload.get("sub", ""),
                email=payload.get("email", ""),
                role=payload.get("role", "authenticated"),
                aud=payload.get("aud", "authenticated"),
                exp=payload.get("exp", 0),
                iat=payload.get("iat", 0)
            )
            
            logger.debug(f"Successfully validated token for user {payload.get("sub")}")
            
            return token_data
            
        except (JWTError, InvalidTokenError) as e:
            logger.error(f"JWT validation error: {str(e)}")
            raise credentials_exception
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            raise credentials_exception
    
    @staticmethod
    def verify_service_role_token(token: str) -> bool:
        """
        Verify if token is a service role token (for admin operations).
        
        Args:
            token: The JWT token string
            
        Returns:
            True if valid service role token
        """
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=[settings.ALGORITHM],
            )
            return payload.get("role") == "service_role"
        except JWTError:
            return False

jwt_validator = JWTValidator()
