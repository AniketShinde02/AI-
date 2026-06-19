from stream_chat import StreamChat
from ..config.settings import settings
from loguru import logger

class VoiceSessionManager:
    def __init__(self):
        logger.debug("Initializing VoiceSessionManager with StreamChat...")
        self.client = StreamChat(
            api_key=settings.STREAM_API_KEY,
            api_secret=settings.STREAM_API_SECRET
        )

    async def create_session(self, user_id: str):
        """Create a WebRTC session token for the frontend."""
        try:
            logger.debug(f"Upserting user {user_id} in Stream...")
            # 1. Create/Update user in Stream
            self.client.upsert_user({"id": user_id, "name": f"Nexus User {user_id}"})
            
            # 2. Generate token (expires in 1 hour)
            logger.debug(f"Creating token for {user_id}...")
            token = self.client.create_token(user_id)
            
            logger.info(f"🔑 Successfully generated Stream token for user: {user_id}")
            
            return {
                "token": token,
                "api_key": settings.STREAM_API_KEY,
                "user_id": user_id
            }
        except Exception as e:
            logger.error(f"❌ Failed to create Stream session: {e}")
            raise

session_manager = VoiceSessionManager()

