from google.cloud import bigquery, storage
from google.api_core import retry
from telethon import TelegramClient, events
from telethon.tl.types import Message, Channel
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any, Optional, NamedTuple
import json
import logging
import os
from hashlib import md5
from openai import AsyncOpenAI


class AnalysisResult(NamedTuple):
    scores: Dict[str, float]
    requires_investigation: bool = False


class InitialAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

        self.analysis_prompt = """Analyze the following message for toxicity and veracity.
Provide scores between 0.0 and 1.0 where:
- toxicity: measure of harmful, threatening, or abusive content
- veracity: likelihood the information is truthful based on known facts
- risk_level: overall risk assessment considering both factors

Message Content:
{text}

Additional Context:
- Channel: {channel_name}
- Has Media: {has_media}
- Views: {views}
- Forwards: {forwards}

Respond in JSON format with only these fields:
{{"toxicity": float, "veracity": float, "risk_level": float, "reasoning": string}}"""

    async def analyze(self, message_data: dict) -> AnalysisResult:
        try:
            # Log input data
            logging.info(f"Analyzing message data: {message_data}")

            # Ensure all values are properly formatted
            formatted_data = {
                "text": str(message_data.get("text", "")).strip() or "No text content",
                "channel_name": str(message_data.get("channel_name", "unknown")),
                "has_media": bool(message_data.get("has_media", False)),
                "views": int(message_data.get("views", 0)),
                "forwards": int(message_data.get("forwards", 0)),
            }

            # Format prompt with sanitized data
            try:
                prompt = self.analysis_prompt.format(**formatted_data)
                logging.info(f"Formatted prompt: {prompt}")
            except KeyError as e:
                logging.error(f"Missing key in prompt formatting: {e}")
                raise
            except Exception as e:
                logging.error(f"Error formatting prompt: {e}")
                raise

            # Prepare message context

            # Call OpenAI API with JSON mode
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content analyzer. Respond only with the requested JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for more consistent scoring
            )
            print(f"Response: {response}")

            # Add detailed logging of the API response
            logging.info(f"Raw API response object: {response}")
            logging.info(f"Response choices: {response.choices}")

            content = response.choices[0].message.content
            logging.info(f"Raw content before cleaning: {repr(content)}")

            # Clean the response string
            content = content.strip()
            content = content.encode().decode("utf-8-sig")
            logging.info(f"Cleaned content: {repr(content)}")

            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error: {str(e)}")
                logging.error(f"Failed content: {repr(content)}")
                # Fallback to safe default scores instead of raising
                return AnalysisResult(
                    scores={"toxicity": 0.0, "veracity": 0.0, "risk_level": 0.0},
                    requires_investigation=False,
                )

            # Validate scores are within bounds
            scores = {
                k: max(0.0, min(1.0, float(v)))
                for k, v in result.items()
                if k in ["toxicity", "veracity", "risk_level"]
            }

            # Log reasoning if provided
            if "reasoning" in result:
                logging.info(f"Analysis reasoning: {result['reasoning']}")

            return AnalysisResult(
                scores=scores,
                requires_investigation=(scores["risk_level"] + scores["toxicity"] > 1),
            )

        except Exception as e:
            logging.error(f"Error in content analysis: {e} {e.__traceback__} {prompt}")
            # Fallback to safe default scores
            return AnalysisResult(
                scores={"toxicity": 0.0, "veracity": 0.0, "risk_level": 0.0},
                requires_investigation=False,
            )


class TelegramMonitor:
    def __init__(
        self,
        client: TelegramClient,
        project_id: str,
        openai_api_key: str,
        bucket_name: str = "telegram_monitor",
        media_folder: str = "media",
    ):
        """
        Initialize the Telegram monitor with BigQuery and Cloud Storage integration.

        Args:
            client: Authenticated TelegramClient instance
            project_id: Google Cloud project ID
            openai_api_key: OpenAI API key
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
        self.initial_analyzer = InitialAnalyzer(api_key=openai_api_key)

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
            bigquery.SchemaField(
                "initial_scores", "STRING"
            ),  # Store JSON string of scores
            bigquery.SchemaField("requires_investigation", "BOOLEAN"),
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
            # @self.client.on(events.MessageEdited(chats=[channel]))
            # async def handle_edited_message(event):
            #     message = event.message
            #     await self._handle_edited_message(message, channel)

            # Store the handlers to prevent garbage collection
            self.handlers.extend([handle_new_message])

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

        try:
            messages = []
            message_tasks = []

            # Just get the 10 most recent messages
            async for message in self.client.iter_messages(channel, limit=10):
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

        # Get analysis results
        analysis_result = await self.initial_analyzer.analyze(
            {
                "text": message.text,
                "channel_name": channel.username or str(channel.id),
                "has_media": bool(message.media),
                "views": getattr(message, "views", 0),
                "forwards": getattr(message, "forwards", 0),
            }
        )

        # Handle replies safely
        replies_count = 0
        if hasattr(message, "replies"):
            replies_count = (
                message.replies.replies if hasattr(message.replies, "replies") else 0
            )

        return {
            "message_id": message.id,
            "channel_id": channel.id,
            "channel_name": channel.username or str(channel.id),
            "date": message.date.isoformat(),
            "text": message.text,
            "views": getattr(message, "views", 0),
            "forwards": getattr(message, "forwards", 0),
            "replies": replies_count,  # Use the safely extracted count
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
            "initial_scores": json.dumps(
                analysis_result.scores
            ),  # Convert dict to JSON string
            "requires_investigation": analysis_result.requires_investigation,
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

    async def get_last_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = f"""
        SELECT *,
        JSON_EXTRACT_SCALAR(initial_scores, '$.toxicity') as toxicity_score,
        JSON_EXTRACT_SCALAR(initial_scores, '$.veracity') as veracity_score,
        JSON_EXTRACT_SCALAR(initial_scores, '$.risk_level') as risk_level
        FROM `{self.dataset_name}.{self.table_name}`
        ORDER BY date DESC
        LIMIT {limit}
        """

        try:
            query_job = self.bq_client.query(query)
            rows = query_job.result()
            messages = []
            for row in rows:
                message = dict(row)
                # Parse scores if they exist
                if message.get("initial_scores"):
                    message["initial_scores"] = json.loads(message["initial_scores"])
                messages.append(message)
            return messages
        except Exception as e:
            self.logger.error(f"Error retrieving messages: {e}")
            return []

    async def _process_message(self, message: Message, channel: Channel):
        """Process a new message with initial analysis"""
        try:
            self.logger.info(
                f"Processing new message {message.id} from channel {channel.username or channel.id}"
            )
            data = await self._prepare_message_data(message, channel)

            # Add initial analysis
            analysis_result = await self.initial_analyzer.analyze(data)
            data["initial_scores"] = analysis_result.scores
            data["requires_investigation"] = analysis_result.requires_investigation

            await self._store_messages([data])

            # Trigger investigation if needed
            if analysis_result.requires_investigation:
                self.logger.info(f"Message {message.id} flagged for investigation")
                # TODO: Implement investigation trigger
                # await self.trigger_investigation(data)

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
