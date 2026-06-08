import datetime
import pyotp
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional

from .config_manager import load_config, save_config, verify_password, hash_password

router = APIRouter(prefix="/api", tags=["Auth & Config"])

class LoginRequest(BaseModel):
    password: str
    totp_code: Optional[str] = None

class Setup2FARequest(BaseModel):
    password: str

class Verify2FARequest(BaseModel):
    totp_code: str

class UpdateConfigRequest(BaseModel):
    is_ocr_public: Optional[bool] = None
    new_password: Optional[str] = None

def create_access_token(data: dict):
    config = load_config()
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config["jwt_secret"], algorithm="HS256")
    return encoded_jwt

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    config = load_config()
    try:
        payload = jwt.decode(token, config["jwt_secret"], algorithms=["HS256"])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_public_or_authenticated(authorization: str = Header(None)):
    config = load_config()
    if config.get("is_ocr_public", True):
        return True
    return get_current_user(authorization)

@router.post("/auth/login")
def login(req: LoginRequest):
    config = load_config()
    if not verify_password(req.password, config["admin_password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")
        
    if config.get("is_2fa_enabled"):
        if not req.totp_code:
            raise HTTPException(status_code=403, detail="2FA required")
        totp = pyotp.TOTP(config["totp_secret"])
        if not totp.verify(req.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
            
    token = create_access_token({"sub": "admin"})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/2fa/setup")
def setup_2fa(req: Setup2FARequest, user=Depends(get_current_user)):
    config = load_config()
    if not verify_password(req.password, config["admin_password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")
        
    secret = pyotp.random_base32()
    # Save temporarily or permanently? Save permanently but not enabled until verified
    config["totp_secret_pending"] = secret
    save_config(config)
    
    # Generate uri for QR code
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name="Admin", issuer_name="UniOCR")
    return {"secret": secret, "uri": uri}

@router.post("/auth/2fa/verify")
def verify_2fa(req: Verify2FARequest, user=Depends(get_current_user)):
    config = load_config()
    pending_secret = config.get("totp_secret_pending")
    if not pending_secret:
        raise HTTPException(status_code=400, detail="No pending 2FA setup")
        
    totp = pyotp.TOTP(pending_secret)
    if not totp.verify(req.totp_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
        
    config["totp_secret"] = pending_secret
    config["is_2fa_enabled"] = True
    config.pop("totp_secret_pending", None)
    save_config(config)
    return {"status": "success"}

@router.post("/auth/2fa/disable")
def disable_2fa(req: Setup2FARequest, user=Depends(get_current_user)):
    config = load_config()
    if not verify_password(req.password, config["admin_password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")
        
    config["totp_secret"] = None
    config["is_2fa_enabled"] = False
    save_config(config)
    return {"status": "success"}

@router.get("/config")
def get_config(user=Depends(get_current_user)):
    config = load_config()
    return {
        "is_ocr_public": config.get("is_ocr_public", True),
        "is_2fa_enabled": config.get("is_2fa_enabled", False),
    }

@router.post("/config")
def update_config(req: UpdateConfigRequest, user=Depends(get_current_user)):
    config = load_config()
    if req.is_ocr_public is not None:
        config["is_ocr_public"] = req.is_ocr_public
    if req.new_password:
        config["admin_password_hash"] = hash_password(req.new_password)
    save_config(config)
    return {"status": "success"}
