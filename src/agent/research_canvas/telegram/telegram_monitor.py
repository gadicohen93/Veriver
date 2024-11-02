from google.cloud import bigquery, storage
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
