
import logging
from multiprocessing import Value
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.supabase_client import get_supabase_publishable_client
from app.infrastructure.repository.business_repository import BusinessRepository
from app.models.dto.auth import LoginRequest, RefreshTokenRequest, SignUpRequest, SignUpResponse, TokenPayload, TokenResponse, UserResponse

logger = logging.getLogger(__name__)

class AuthService():
    
    def __init__(self, db: AsyncSession) -> None:
        self.supabase_client = get_supabase_publishable_client()
        self.db = db
        
    
    async def signup_user(self, signup_data: SignUpRequest) -> SignUpResponse:            
        try:
            # Sign up with Supabase
            response = self.supabase_client.auth.sign_up({
                "email": signup_data.email,
                "password": signup_data.password,
                "options": {
                    "data": {
                        "full_name": signup_data.full_name
                    }
                }
            })
            
            if response.user is None:
                raise ConnectionError(f"failed to create user with supa base for email: {signup_data.email}")
            
            business_repo = BusinessRepository(self.db)
            business = await business_repo.create(
                user_id=response.user.id,
                email=signup_data.email,
                name=signup_data.full_name or signup_data.email.split('@')[0],
                subdomain=signup_data.email.split('@')[1].lower(),
                created_at=response.user.created_at
            )
            
            print(business)
            
            logger.info(f"Created new user and business: {response.user.id}")
            
            return SignUpResponse(
                user=UserResponse(id=response.user.id, email=signup_data.email, created_at=response.user.created_at),
                access_token=response.session.access_token if response.session else "",
                refresh_token=response.session.refresh_token if response.session else None,
                message="User created successfully"
            )
            
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            raise e
        
    
    async def login_user(self, login_data: LoginRequest):
        """
        Authenticate user and return JWT token.
        """
        try:
            response = self.supabase_client.auth.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            
            if response.user is None or response.session is None:
                raise ValueError("Invalid email or password")
            
            
            return TokenResponse(
                access_token=response.session.access_token,
                token_type="bearer",
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in,
                user=UserResponse(
                    id=response.user.id,
                    email=login_data.email,
                    created_at=response.user.created_at
                )
            )
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise e
        
    
    async def refresh_token(self, refresh_data: RefreshTokenRequest):
        try:
            response = self.supabase_client.auth.refresh_session(refresh_data.refresh_token)
        
            if response.session is None:
                raise ValueError("Invalid refresh token")
            
            if response.user is None:
                raise ValueError("Invalid refresh token")
            
            return TokenResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                token_type="bearer",
                expires_in=response.session.expires_in,
                user=UserResponse(
                    id=response.user.id,
                    email=response.user.email, # type: ignore
                    created_at=response.user.created_at
                )
            )
        except Exception as e:
            logger.error(f"Refresh error: {str(e)}")
            raise e
        
    async def logout_user(self, current_user: TokenPayload):
        try:
            self.supabase_client.auth.sign_out()
            logger.info(f"User logged out: {current_user.sub}")
            return {"message": "Successfully logged out"}
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise e
        