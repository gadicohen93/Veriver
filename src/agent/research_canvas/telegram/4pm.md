You're the world's leading expert on disinformation detection and AI engineer.

I'm currently building an AI agent that can analyze messages from Telegram channels.

Help me determine my next steps.

Currently working code:

# demo.py
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


#from google.cloud import bigquery, storage
from google.api_core import retry
from telethon import TelegramClient, events
from telethon.tl.types import Message, Channel
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any, Optional
import json
import logging
import os
from hashlib import md5


class TelegramMonitor:
    def __init__(
        self,
        client: TelegramClient,
        project_id: str,
        bucket_name: str = "telegram_monitor",
        media_folder: str = "media",
    ):
        """
        Initialize the Telegram monitor with BigQuery and Cloud Storage integration.

        Args:
            client: Authenticated TelegramClient instance
            project_id: Google Cloud project ID
            bucket_name: Google Cloud Storage bucket for media files
            media_folder: Local folder for temporary media storage
        """
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)

        self.logger.info(f"Initializing TelegramMonitor with project_id: {project_id}")

        # Initialize clients and settings
        self.client = client
        self.bq_client = bigquery.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        self.bucket = self.storage_client.bucket(bucket_name)
        self.media_folder = media_folder
        self.dataset_name = "telegram_monitor"
        self.table_name = "channel_messages"

        # Create media folder if it doesn't exist
        os.makedirs(media_folder, exist_ok=True)

        # Initialize BigQuery resources
        self._ensure_bigquery_resources()

        self.handlers = []  # Add this to store handlers

    def _ensure_bigquery_resources(self):
        """Create BigQuery dataset and table if they don't exist."""
        self.logger.debug("Ensuring BigQuery resources exist")
        dataset_ref = self.bq_client.dataset(self.dataset_name)

        # Create dataset if it doesn't exist
        try:
            self.bq_client.get_dataset(dataset_ref)
        except Exception:
            self.logger.info(f"Creating dataset {self.dataset_name}")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.bq_client.create_dataset(dataset)

        # Enhanced schema with media handling
        schema = [
            bigquery.SchemaField("message_id", "INTEGER"),
            bigquery.SchemaField("channel_id", "INTEGER"),
            bigquery.SchemaField("channel_name", "STRING"),
            bigquery.SchemaField("date", "TIMESTAMP"),
            bigquery.SchemaField("text", "STRING"),
            bigquery.SchemaField("views", "INTEGER"),
            bigquery.SchemaField("forwards", "INTEGER"),
            bigquery.SchemaField("replies", "INTEGER"),
            bigquery.SchemaField("has_media", "BOOLEAN"),
            bigquery.SchemaField("media_type", "STRING"),
            bigquery.SchemaField("media_urls", "STRING", mode="REPEATED"),
            bigquery.SchemaField("processed", "BOOLEAN"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("edited", "BOOLEAN"),
            bigquery.SchemaField("edited_at", "TIMESTAMP"),
            bigquery.SchemaField("is_pinned", "BOOLEAN"),
            bigquery.SchemaField("has_reactions", "BOOLEAN"),
            bigquery.SchemaField(
                "reaction_counts", "STRING"
            ),  # JSON string of reaction counts
        ]

        table_ref = dataset_ref.table(self.table_name)
        try:
            self.bq_client.get_table(table_ref)
        except Exception:
            self.logger.info(f"Creating table {self.table_name}")
            table = bigquery.Table(table_ref, schema=schema)
            self.bq_client.create_table(table)

    async def subscribe_to_channel(self, channel_username: str) -> tuple[bool, str]:
        """
        Subscribe to a Telegram channel and start monitoring messages.
        Loads messages from the last hour and sets up monitoring for new messages.

        Args:
            channel_username: Channel username or invite link

        Returns:

            Tuple of (success, message)
        """
        self.logger.info(f"Attempting to subscribe to channel: {channel_username}")
        try:
            # Clean up channel username
            if channel_username.startswith("https://t.me/"):
                channel_username = channel_username.split("/")[-1]
            elif channel_username.startswith("@"):
                channel_username = channel_username[1:]

            # Get channel entity
            channel = await self.client.get_entity(channel_username)
            if not isinstance(channel, Channel):
                return False, "Not a valid channel"

            # Start monitoring new messages
            @self.client.on(events.NewMessage(chats=[channel]))
            async def handle_new_message(event):
                message = event.message
                await self._process_message(message, channel)

            # Monitor message edits
            @self.client.on(events.MessageEdited(chats=[channel]))
            async def handle_edited_message(event):
                message = event.message
                await self._handle_edited_message(message, channel)

            # Store the handlers to prevent garbage collection
            self.handlers.extend([handle_new_message, handle_edited_message])

            # Load recent messages (last hour)
            await self._load_recent_messages(channel)

            return True, f"Successfully subscribed to {channel_username}"

        except Exception as e:
            self.logger.error(f"Error subscribing to channel {channel_username}: {e}")
            return False, str(e)

    async def _load_recent_messages(self, channel: Channel):
        """Load the 10 most recent messages with parallel processing."""
        self.logger.info(
            f"Loading 10 most recent messages for channel {channel.username or channel.id}"
        )
        min_date = datetime.now() - timedelta(hours=1)

        try:
            messages = []
            message_tasks = []

            # Limit to 10 messages
            async for message in self.client.iter_messages(
                channel, limit=10, offset_date=min_date, reverse=True
            ):
                task = asyncio.create_task(self._prepare_message_data(message, channel))
                message_tasks.append(task)

            # Process all messages at once since we're only handling 10
            if message_tasks:
                batch_results = await asyncio.gather(*message_tasks)
                messages.extend(batch_results)
                await self._store_messages(messages)

            self.logger.info(f"Successfully loaded {len(messages)} recent messages")

        except Exception as e:
            self.logger.error(f"Error loading messages: {e}")
            raise

    async def _handle_media(self, message: Message) -> List[str]:
        """
        Download and upload media to Cloud Storage, return media URLs.
        """
        if not message.media:
            return []

        media_urls = []
        try:
            # Generate unique filename using message ID and MD5 hash
            base_filename = (
                f"{message.id}_{md5(str(message.date).encode()).hexdigest()[:8]}"
            )

            # Download media
            path = await message.download_media(
                file=f"{self.media_folder}/{base_filename}"
            )

            if path:
                # Upload to Cloud Storage
                blob_path = f"channel_{message.chat_id}/{base_filename}"
                blob = self.bucket.blob(blob_path)
                blob.upload_from_filename(path)

                # Get the public URL without trying to modify ACLs
                media_urls.append(
                    f"https://storage.googleapis.com/{self.bucket.name}/{blob_path}"
                )

                # Clean up local file
                os.remove(path)

        except Exception as e:
            self.logger.error(f"Error handling media for message {message.id}: {e}")

        return media_urls

    async def _prepare_message_data(
        self, message: Message, channel: Channel
    ) -> Dict[str, Any]:
        """Prepare message data for storage with enhanced media handling."""
        media_type = None
        media_urls = []

        if message.media:
            media_type = type(message.media).__name__
            media_urls = await self._handle_media(message)

        # Handle reactions if available
        reactions = {}
        if hasattr(message, "reactions") and message.reactions:
            for reaction in message.reactions.results:
                reactions[reaction.reaction.emoticon] = reaction.count

        return {
            "message_id": message.id,
            "channel_id": channel.id,
            "channel_name": channel.username or str(channel.id),
            "date": message.date.isoformat(),
            "text": message.text,
            "views": getattr(message, "views", 0),
            "forwards": getattr(message, "forwards", 0),
            "replies": (
                getattr(message, "replies", 0) if hasattr(message, "replies") else 0
            ),
            "has_media": bool(message.media),
            "media_type": media_type,
            "media_urls": media_urls,
            "processed": False,
            "created_at": datetime.now().isoformat(),
            "edited": message.edit_date is not None,
            "edited_at": message.edit_date.isoformat() if message.edit_date else None,
            "is_pinned": message.pinned,
            "has_reactions": bool(reactions),
            "reaction_counts": json.dumps(reactions) if reactions else None,
        }

    async def _handle_edited_message(self, message: Message, channel: Channel):
        """Handle edited messages by updating the database record."""
        try:
            data = await self._prepare_message_data(message, channel)

            query = f"""
            UPDATE `{self.dataset_name}.{self.table_name}`
            SET 
                text = @text,
                views = @views,
                forwards = @forwards,
                replies = @replies,
                edited = @edited,
                edited_at = @edited_at,
                has_reactions = @has_reactions,
                reaction_counts = @reaction_counts
            WHERE message_id = @message_id AND channel_id = @channel_id
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("text", "STRING", data["text"]),
                    bigquery.ScalarQueryParameter("views", "INTEGER", data["views"]),
                    bigquery.ScalarQueryParameter(
                        "forwards", "INTEGER", data["forwards"]
                    ),
                    bigquery.ScalarQueryParameter(
                        "replies", "INTEGER", data["replies"]
                    ),
                    bigquery.ScalarQueryParameter("edited", "BOOLEAN", data["edited"]),
                    bigquery.ScalarQueryParameter(
                        "edited_at", "TIMESTAMP", data["edited_at"]
                    ),
                    bigquery.ScalarQueryParameter(
                        "has_reactions", "BOOLEAN", data["has_reactions"]
                    ),
                    bigquery.ScalarQueryParameter(
                        "reaction_counts", "STRING", data["reaction_counts"]
                    ),
                    bigquery.ScalarQueryParameter(
                        "message_id", "INTEGER", data["message_id"]
                    ),
                    bigquery.ScalarQueryParameter(
                        "channel_id", "INTEGER", data["channel_id"]
                    ),
                ]
            )

            query_job = self.bq_client.query(query, job_config=job_config)
            query_job.result()

        except Exception as e:
            self.logger.error(f"Error handling edited message: {e}")

    @retry.Retry(predicate=retry.if_exception_type(Exception))
    async def _store_messages(self, messages: List[Dict[str, Any]]):
        """Store messages in BigQuery with enhanced retry logic."""
        if not messages:
            return

        try:
            table_ref = self.bq_client.dataset(self.dataset_name).table(self.table_name)
            errors = self.bq_client.insert_rows_json(table_ref, messages)

            if errors:
                self.logger.error(f"Errors inserting rows: {errors}")
                raise Exception(f"Failed to insert rows: {errors}")

        except Exception as e:
            self.logger.error(f"Error storing messages: {e}")
            raise

    async def get_recent_messages(self, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Retrieve recent messages from BigQuery.
        """
        query = f"""
        SELECT *
        FROM `{self.dataset_name}.{self.table_name}`
        WHERE date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        ORDER BY date DESC
        """

        try:
            query_job = self.bq_client.query(query)
            rows = query_job.result()
            return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Error retrieving messages: {e}")
            return []

    async def _process_message(self, message: Message, channel: Channel):
        """Process a new message"""
        try:
            data = await self._prepare_message_data(message, channel)
            await self._store_messages([data])
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")


Some brainstorming:
- We want on new message to analyze for initial scores (for example, toxicity or veracity scores) 
- the AI agent will pick up new messages that were initially flagged with a high toxicity, low veracity scores and figure out what is needed to investigate 
- AI agent tasks could include:
	- send images or videos to Gemini [to try to extract any possible information to help in disinformation detection, for example location, date, people involved, etc, to figure out if they match the text and context]
	- pull from a possible trusted News API and figure out if the post matches it
	- etc.?
- The agent should autonomously work through those actions for a post and come up with a final score, at which point it should alert the user in some way for intervention


Some dependencies we have to use:

- CopilotKit
- Gemini 
- Must incorporate human-in-the-loop in an elevated way


Note, for context, a working example of a CopilotKit demo:
