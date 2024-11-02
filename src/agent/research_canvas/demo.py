"""Demo with Telegram integration"""

import os
from dotenv import load_dotenv
from research_canvas.telegram.telegram_monitor import TelegramMonitor

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent
from research_canvas.agent import graph
from typing import Optional
from telethon.sessions import StringSession
from contextlib import asynccontextmanager
import logging
from google.cloud import bigquery
from typing import List
import json
from datetime import datetime, timedelta

# Import the TelegramAuthManager
from .telegram.auth_manager import TelegramAuthManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Request/Response Models
class ChannelSubscription(BaseModel):
    channel: str  # @username or https://t.me/username


class TelegramAuth(BaseModel):
    phone: str
    code: Optional[str] = None
    password: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    message: str


# Global state manager for telegram client
telegram_manager: Optional[TelegramAuthManager] = None


# Add these models
class ChannelMessage(BaseModel):
    message_id: int
    channel_name: str
    date: datetime
    text: str
    views: Optional[int]
    forwards: Optional[int]
    has_media: bool
    media_type: Optional[str]


class MessageResponse(BaseModel):
    messages: List[ChannelMessage]


# Add this to your global state
telegram_monitor = None


# Update your lifespan function
@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_manager, telegram_monitor

    # Initialize TelegramAuthManager
    telegram_manager = TelegramAuthManager()
    try:
        success, message = await telegram_manager.initialize_client()
        if not success:
            logger.warning(f"Telegram client initialization warning: {message}")
        else:
            # Initialize TelegramMonitor if client is ready
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if project_id:
                telegram_monitor = TelegramMonitor(telegram_manager.client, project_id)
            else:
                logger.warning("GOOGLE_CLOUD_PROJECT environment variable not set")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram client: {e}")

    yield

    # Cleanup
    if telegram_manager:
        await telegram_manager.close()


app = FastAPI(lifespan=lifespan)

# Add CopilotKit SDK
sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="research_agent",
            description="Research agent.",
            agent=graph,
        )
    ],
)

add_fastapi_endpoint(app, sdk, "/copilotkit")


# Dependency to check telegram client
async def get_telegram_client():
    if not telegram_manager:
        raise HTTPException(status_code=500, detail="Telegram client not initialized")
    if not telegram_manager.client:
        raise HTTPException(status_code=401, detail="Telegram client not authenticated")
    return telegram_manager


# Update your subscribe endpoint
@app.post("/telegram/subscribe", response_model=AuthResponse)
async def subscribe_to_channel(
    subscription: ChannelSubscription,
    client: TelegramAuthManager = Depends(get_telegram_client),
):
    """Subscribe to a Telegram channel"""
    try:
        if not telegram_monitor:
            raise HTTPException(
                status_code=500, detail="Telegram monitor not initialized"
            )

        success, message = await telegram_monitor.subscribe_to_channel(
            subscription.channel
        )
        return AuthResponse(success=success, message=message)

    except Exception as e:
        logger.error(f"Channel subscription error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Add new endpoint to get recent messages
@app.get("/telegram/messages", response_model=MessageResponse)
async def get_messages(
    hours: int = 1,
    client: TelegramAuthManager = Depends(get_telegram_client),
):
    """Get recent messages from monitored channels"""
    try:
        if not telegram_monitor:
            raise HTTPException(
                status_code=500, detail="Telegram monitor not initialized"
            )

        messages = await telegram_monitor.get_recent_messages(hours)
        return MessageResponse(messages=messages)

    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/telegram/auth", response_model=AuthResponse)
async def authenticate_telegram(auth_data: TelegramAuth):
    """Handle Telegram authentication"""
    if not telegram_manager:
        raise HTTPException(status_code=500, detail="Telegram client not initialized")

    try:
        # If code is provided, complete the login
        if auth_data.code:

            async def code_callback():
                return auth_data.code

            success, message = await telegram_manager.login(
                phone=auth_data.phone, code_callback=code_callback
            )
        else:
            # Initial authentication request
            success, message = await telegram_manager.initialize_client()
            if not success and "not authorized" in message:
                success, message = await telegram_manager.login(phone=auth_data.phone)

        return AuthResponse(success=success, message=message)

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/telegram/status")
async def get_status(client: TelegramAuthManager = Depends(get_telegram_client)):
    """Get Telegram client status"""
    try:
        is_authorized = await client.client.is_user_authorized()
        return {
            "status": "authorized" if is_authorized else "unauthorized",
            "session_file_exists": client.session_file.exists(),
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("research_canvas.demo:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
