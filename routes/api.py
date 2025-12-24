from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.telegram_client import client_manager
from services.storage import storage_service

router = APIRouter()

class LoginRequest(BaseModel):
    phone: str

class VerifyRequest(BaseModel):
    code: str
    password: str = None

@router.get("/status")
async def status():
    return {"status": "ok", "service": "opdeals-backend"}

@router.post("/auth/login")
async def login(request: LoginRequest):
    try:
        res = await client_manager.send_code(request.phone)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/verify")
async def verify(request: VerifyRequest):
    try:
        res = await client_manager.verify_code(request.code, request.password)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/deals")
async def get_deals():
    return storage_service.get_deals()
