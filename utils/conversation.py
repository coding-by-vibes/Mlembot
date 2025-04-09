import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
import asyncio
import openai

@dataclass
class Message:
    role: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]

@dataclass
class Conversation:
    messages: List[Message]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

class ConversationManager:
    def __init__(self, settings_dir: str) -> None:
        self.settings_dir = settings_dir
        self.conversations_dir = os.path.join(settings_dir, "conversations")
        self.logger = logging.getLogger(__name__)
        os.makedirs(self.conversations_dir, exist_ok=True)

        self.default_settings = {
            "max_history": 10,
            "auto_summarize": False,
            "language": "en",
            "temperature": 0.7,
            "max_tokens": 1000,
            "model": "gpt-4o-mini",
            "system_prompt": "You are a helpful AI assistant. Your responses should be clear and concise."
        }

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        openai.api_key = api_key
        self.logger.info("OpenAI client initialized successfully")

    async def create_conversation(self, conversation_id: str, settings: Optional[Dict[str, Any]] = None) -> Conversation:
        settings = settings or {}
        conversation_settings = {**self.default_settings, **settings}

        conversation = Conversation(
            messages=[],
            context={},
            metadata={
                "settings": conversation_settings,
                "topic": None,
                "sentiment": None,
                "participants": set()
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        await self._save_conversation(conversation_id, conversation)
        return conversation

    async def get_conversation(self, user_id: str, channel_id: str) -> Optional[Conversation]:
        try:
            import aiofiles
            conversation_id = f"{user_id}_{channel_id}"
            file_path = os.path.join(self.conversations_dir, f"{conversation_id}.json")
            if not os.path.exists(file_path):
                return None

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
                return self._deserialize_conversation(data)
        except Exception as e:
            self.logger.error(f"Error getting conversation for user {user_id} in channel {channel_id}: {e}", exc_info=True)
            return None

    async def add_message(self, user_id: str, channel_id: str, content: str, role: str = "user", conversation: Optional[Conversation] = None, system_prompt: Optional[str] = None) -> Optional[Conversation]:
        try:
            conversation_id = f"{user_id}_{channel_id}"
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "message_type": "text"
                }
            )

            if conversation is None:
                conversation = await self.get_conversation(user_id, channel_id)
                if not conversation:
                    conversation = Conversation(
                        messages=[],
                        context={},
                        metadata={
                            "settings": self.default_settings.copy(),
                            "topic": None,
                            "sentiment": None,
                            "participants": set()
                        },
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )

            if "participants" not in conversation.metadata:
                conversation.metadata["participants"] = set()

            # Update system prompt if provided
            if system_prompt:
                conversation.metadata["settings"]["system_prompt"] = system_prompt

            conversation.messages.append(message)
            conversation.metadata["participants"].add(role)
            conversation.updated_at = datetime.now().isoformat()
            await self._save_conversation(conversation_id, conversation)
            return conversation
        except Exception as e:
            self.logger.error(f"Error adding message to conversation: {e}", exc_info=True)
            return None

    async def generate_response(self, user_id: str, channel_id: str, message: str, conversation: Optional[Conversation] = None) -> Optional[str]:
        try:
            if not conversation:
                conversation = await self.get_conversation(user_id, channel_id)
                if not conversation:
                    conversation = await self.create_conversation(f"{user_id}_{channel_id}")

            if "participants" not in conversation.metadata:
                conversation.metadata["participants"] = set()

            user_message = Message(
                role="user",
                content=message,
                timestamp=datetime.now().isoformat(),
                metadata={}
            )
            conversation.messages.append(user_message)
            conversation.metadata["participants"].add("user")
            conversation.updated_at = datetime.now().isoformat()

            response_text = await self._generate_ai_response(conversation)

            ai_message = Message(
                role="assistant",
                content=response_text,
                timestamp=datetime.now().isoformat(),
                metadata={}
            )
            conversation.messages.append(ai_message)
            conversation.metadata["participants"].add("assistant")
            conversation.updated_at = datetime.now().isoformat()

            await self._save_conversation(f"{user_id}_{channel_id}", conversation)
            return response_text
        except Exception as e:
            self.logger.error(f"Error generating response for user {user_id} in channel {channel_id}: {e}", exc_info=True)
            return None

    async def _generate_ai_response(self, conversation: Conversation) -> str:
        try:
            recent_messages = conversation.messages[-5:]
            messages = []
            
            # Add system prompt if available
            settings = conversation.metadata.get("settings", self.default_settings)
            system_prompt = settings.get("system_prompt")
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation messages
            messages.extend([{"role": msg.role, "content": msg.content} for msg in recent_messages])

            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=settings.get("model", "gpt-4o-mini"),
                messages=messages,
                temperature=settings.get("temperature", 0.7),
                max_tokens=settings.get("max_tokens", 1000)
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}", exc_info=True)
            return "I'm sorry, I encountered an error while generating a response."

    async def _save_conversation(self, conversation_id: str, conversation: Conversation):
        try:
            import aiofiles
            file_path = os.path.join(self.conversations_dir, f"{conversation_id}.json")
            os.makedirs(self.conversations_dir, exist_ok=True)
            data = self._serialize_conversation(conversation)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}", exc_info=True)
            raise

    def _serialize_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        return {
            "messages": [asdict(msg) for msg in conversation.messages],
            "context": conversation.context,
            "metadata": {
                **conversation.metadata,
                "participants": list(conversation.metadata.get("participants", set()))
            },
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }

    def _deserialize_conversation(self, data: Dict[str, Any]) -> Conversation:
        return Conversation(
            messages=[Message(**msg) for msg in data["messages"]],
            context=data["context"],
            metadata={
                **data["metadata"],
                "participants": set(data["metadata"].get("participants", []))
            },
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

    async def reset_conversation(self, user_id: str, channel_id: str) -> None:
        """
        Deletes the conversation file for the given user and channel, effectively resetting it.
        """
        try:
            conversation_id = f"{user_id}_{channel_id}"
            file_path = os.path.join(self.conversations_dir, f"{conversation_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Conversation {conversation_id} reset successfully.")
            else:
                self.logger.warning(f"No conversation found to reset for {conversation_id}")
        except Exception as e:
            self.logger.error(f"Error resetting conversation {conversation_id}: {e}", exc_info=True)