from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import api
import uvicorn
import os
from dotenv import load_dotenv
from services.telegram_client import client_manager
from services.scraper import scraper_service
from services.storage import storage_service
import re
from contextlib import asynccontextmanager

load_dotenv()

def _parse_cors_origins(value: str | None):
    if not value:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    items = []
    for part in value.split(","):
        v = part.strip()
        if not v:
            continue
        if v.endswith("/"):
            v = v[:-1]
        items.append(v)
    return items or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

origins = _parse_cors_origins(os.getenv("FRONTEND_ORIGIN"))

async def handle_new_message(event):
    if not event.message or not event.message.message:
        return
    # Process only messages from the configured channel id
    try:
        channel_id = client_manager.channel_id
        if getattr(event, "chat_id", None) != channel_id:
            return
    except Exception:
        pass
    message_text = event.message.message
    # Simple regex for links
    urls = re.findall(r'(https?://[^\s]+)', message_text)
    
    for url in urls:
        print(f"Found URL: {url}")
        # Pass to scraper to determine if it's a valid deal link (resolves shorteners)
        deal = await scraper_service.scrape(url)
        if deal:
            print(f"Scraped deal: {deal['title']}")
            storage_service.save_deal(deal)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await client_manager.start_listening(handle_new_message)
    except Exception as e:
        print(f"Could not start listener: {e}")
    # App is running
    yield
    # Shutdown cleanup
    try:
        if getattr(client_manager, "client", None):
            await client_manager.client.disconnect()
    except Exception as e:
        print(f"Could not cleanly disconnect: {e}")

app = FastAPI(title="OPDEALS Backend", version="1.0.0", lifespan=lifespan)

def _parse_cors_origins(value: str | None):
    if not value:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    items = []
    for part in value.split(","):
        v = part.strip()
        if not v:
            continue
        # Strip trailing slash to match browser origin format
        if v.endswith("/"):
            v = v[:-1]
        items.append(v)
    return items or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

# CORS Middleware
origins = _parse_cors_origins(os.getenv("FRONTEND_ORIGIN"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routes
app.include_router(api.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "OPDEALS Backend is running"}

# Startup handled via lifespan()

if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
