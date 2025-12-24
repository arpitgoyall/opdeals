from telethon import TelegramClient, events
import os
import asyncio
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramClientManager:
    def __init__(self):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.client = None
        self.phone = None
        self.session_name = 'opdeals_session'
        # Restrict listener to a specific channel id (env override allowed)
        self.channel_id = int(os.getenv("TELEGRAM_CHANNEL_ID", "-1003651699920"))

    async def ensure_connected(self):
        if not self.api_id or not self.api_hash:
            # Attempt to load from .env if not already loaded or when running under reload
            load_dotenv()
            self.api_id = os.getenv("TELEGRAM_API_ID")
            self.api_hash = os.getenv("TELEGRAM_API_HASH")
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH not set in environment")
        
        if self.client is None:
            self.client = TelegramClient(self.session_name, int(self.api_id), self.api_hash)
        
        if not self.client.is_connected():
            await self.client.connect()

    async def send_code(self, phone):
        await self.ensure_connected()
        self.phone = phone
        if await self.client.is_user_authorized():
            return {"status": "already_authorized"}
        
        try:
            sent = await self.client.send_code_request(phone)
            return {"status": "code_sent", "phone_code_hash": sent.phone_code_hash}
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            raise e

    async def verify_code(self, code, password=None):
        await self.ensure_connected()
        try:
            await self.client.sign_in(self.phone, code, password=password)
            return {"status": "authorized"}
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            raise e

    async def start_listening(self, callback):
        await self.ensure_connected()
        
        @self.client.on(events.NewMessage(chats=self.channel_id))
        async def handler(event):
            await callback(event)
            
        logger.info("Started listening for new messages...")

client_manager = TelegramClientManager()
