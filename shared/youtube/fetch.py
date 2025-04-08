
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import logging

class YouTubeManager:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.logger = logging.getLogger(__name__)

    async def get_video_details(self, video_url: str) -> dict:
        video_id = video_url.split("v=")[-1]
        request = self.youtube.videos().list(
            part="snippet",
            id=video_id
        )
        response = request.execute()
        if not response["items"]:
            raise ValueError("Video not found")
        return response["items"][0]["snippet"]

def get_transcript(video_id: str) -> str:
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return "\n".join(entry["text"] for entry in transcript)
