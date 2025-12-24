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

load_dotenv()

app = FastAPI(title="OPDEALS Backend", version="1.0.0")

# CORS Middleware
front_origin = os.getenv("FRONTEND_ORIGIN")
origins = [front_origin] if front_origin else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

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

@app.on_event("startup")
async def startup_event():
    try:
        await client_manager.start_listening(handle_new_message)
    except Exception as e:
        print(f"Could not start listener: {e}")

if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
