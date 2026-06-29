# Auth service — wraps Swabi login / logout API calls.

from app.services.swabi_client import swabi_client
from app.core.auth import AuthUser, decode_swabi_token

async def login(email: str, password:str)-> dict:
    
    """
    Authenticate against Swabi. Sends the full required payload.
    Returns dict with auth_user (AuthUser) and raw (Swabi data dict).
    Raises httpx.HTTPStatusError on 4xx/5xx from Swabi.
    Raises HTTPException (via decode_swabi_token) if token invalid.
    """
      
    response = await swabi_client.post(
        "/login",{
            "TokenType": "WEB",
            "email": email,
            "password": password,
            "userType": "USER",
            "notificationToken": "",
            "zoneId": "Asia/Calcutta",
        },
    )
    data = response.get("data",{})
    token = data.get("token","")
    
    # Decode and validate the JWT - raises HTTPException if invalid
    auth_user = decode_swabi_token(token)
    
    # Patch first/last name from login response (not in JWT payload)
    auth_user = AuthUser(
        user_id=auth_user.user_id,
        user_type=auth_user.user_type,
        email=auth_user.email,
        first_name = data.get("first_Name",""),
        last_name = data.get("lastName",""),
        token = token,
    )
    
    return {
        "auth_user": auth_user,
        "raw": data,
    }
    
async def logout(user_id: int, token:str)-> dict:
    "Invalidate the user's session on Swabi."
    "GET /logout_user?userType=USER&userId=<id>  with Bearer token."
    
    return await swabi_client.get_authed(
        f"/logout_user?userType=USER&userId={user_id}",
        token = token,
    )