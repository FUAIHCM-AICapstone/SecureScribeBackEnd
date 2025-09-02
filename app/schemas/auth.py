from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class GoogleAuthRequest(BaseModel):
    id_token: str
class AuthResponse(BaseModel):
    user: dict
    token: TokenResponse
