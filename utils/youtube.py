from typing import Dict, List, Optional, Union
import os
import re
from datetime import datetime
import logging
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from summarizer.summarizer import summarize_article_full
from utils.discord_utils import fix_discord_formatting
from config.config import YOUTUBE_API_KEY
import openai
# from utils.recipe import RecipeDetector
import asyncio

# recipe_detector = RecipeDetector()


async def process_youtube_video(video_id: str, summary_type: str = "default") -> dict:
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    text = "\n".join(entry["text"] for entry in transcript)
    print("[Transcript Preview]", text[:50], "...")

    # recipe = recipe_detector.detect_recipe(text)
    # if recipe:
    #     return {
    #         "type": "recipe",
    #         "title": recipe["title"],
    #         "markdown": recipe["markdown"],
    #         "raw": recipe,
    #         "source": f"https://www.youtube.com/watch?v={video_id}"
    #     }

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    video_title = f"YouTube Video ({video_id})"

    try:
        yt = YouTubeManager(YOUTUBE_API_KEY)
        details = await yt.get_video_details(video_url)
        video_title = details["title"]
    except Exception:
        pass

    summary = await summarize_article_full(
        text=text,
        summary_type=summary_type,
        title=video_title,
        url=video_url
    )

    return {
        "type": "summary",
        "summary": summary,
        "source": video_url
    }


class YouTubeManager:
    def __init__(self, api_key: str):
        """Initialize the YouTube manager.
        
        Args:
            api_key: YouTube API key
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.logger = logging.getLogger(__name__)
        # self.recipe_manager = RecipeManager()
        self.formatter = TextFormatter()
        
        # Configure DeepSeek API
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        
        # Configure logger to handle Unicode
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setStream(open(handler.stream.fileno(), mode=handler.stream.mode, encoding='utf-8'))
            elif isinstance(handler, logging.FileHandler):
                handler.setStream(open(handler.baseFilename, mode=handler.mode, encoding='utf-8'))
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats.
        
        Args:
            url: YouTube video URL
            
        Returns:
            str: Video ID if found, None otherwise
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu.be\/|youtube.com\/embed\/)([^&\n?#]+)',
            r'youtube.com\/shorts\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_video_details(self, url: str) -> Dict:
        """Get video details from YouTube API."""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            # Get video details from YouTube API
            try:
                request = self.youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=video_id
                )
                response = request.execute()
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"YouTube API error: {error_msg}")
                
                # Handle specific API errors
                if "quotaExceeded" in error_msg:
                    raise ValueError("YouTube API quota exceeded. Please try again later.")
                elif "invalidApiKey" in error_msg:
                    raise ValueError("Invalid YouTube API key. Please contact the bot administrator.")
                elif "videoNotFound" in error_msg:
                    raise ValueError("Video not found or not accessible")
                else:
                    raise ValueError(f"Failed to fetch video details: {error_msg}")

            if not response.get('items'):
                raise ValueError("Video not found or not accessible")

            video = response['items'][0]
            
            return {
                'title': video['snippet']['title'],
                'channel': video['snippet']['channelTitle'],
                'duration': video['contentDetails']['duration'],
                'views': int(video['statistics']['viewCount']),
                'thumbnail': video['snippet']['thumbnails']['high']['url'] if 'thumbnails' in video['snippet'] else None
            }
        except ValueError as ve:
            self.logger.error(f"Value error in get_video_details: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in get_video_details: {str(e)}")
            raise ValueError(f"An unexpected error occurred: {str(e)}")
    
    async def get_transcript(self, url: str, detailed: bool = False) -> Optional[Dict]:
        """Get transcript and recipe (if available) from YouTube video.
        
        Returns:
            Dict containing:
            - transcript: The video transcript
            - recipe: Optional recipe information if detected
        """
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                self.logger.error("Invalid YouTube URL")
                return None

            # Get transcript list
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error getting transcript list: {error_msg}")
                if "videoNotFound" in error_msg:
                    self.logger.error(f"Video {video_id} not found")
                    return None
                elif "transcriptsDisabled" in error_msg:
                    self.logger.error(f"Transcripts are disabled for video {video_id}")
                    return None
                else:
                    self.logger.error(f"Unexpected error getting transcript list: {error_msg}")
                    return None
            
            # Try to get manual English transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                self.logger.info(f"Found manual English transcript for video {video_id}")
            except Exception as e:
                self.logger.info(f"No manual English transcript found for video {video_id}, trying auto-generated")
                # If no manual transcript, try auto-generated English
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    self.logger.info(f"Found auto-generated English transcript for video {video_id}")
                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"Failed to get English transcript for video {video_id}: {error_msg}")
                    if "transcriptsDisabled" in error_msg:
                        self.logger.error(f"Auto-generated transcripts are disabled for video {video_id}")
                        return None
                    elif "noTranscriptFound" in error_msg:
                        self.logger.error(f"No English transcript available for video {video_id}")
                        return None
                    else:
                        self.logger.error(f"Unexpected error getting auto-generated transcript: {error_msg}")
                        return None

            # Get transcript
            try:
                transcript_data = transcript.fetch()
                if not transcript_data:
                    self.logger.error(f"Empty transcript data received for video {video_id}")
                    return None
                    
                formatted_transcript = self.formatter.format_transcript(transcript_data)
                if not formatted_transcript:
                    self.logger.error(f"Empty formatted transcript for video {video_id}")
                    return None
                    
                self.logger.info(f"Successfully fetched transcript for video {video_id}")
            except Exception as e:
                self.logger.error(f"Error fetching or formatting transcript: {str(e)}")
                return None
            
            result = {'transcript': formatted_transcript}
            
            # Check if transcript contains a recipe
            try:
                if self.recipe_manager.is_recipe_content(formatted_transcript):
                    self.logger.info(f"Detected recipe content in video {video_id}")
                    recipe = self.recipe_manager.extract_recipe(formatted_transcript, url)
                    if recipe:
                        self.logger.info(f"Successfully extracted recipe from video {video_id}")
                        recipe_cards = self.recipe_manager.format_recipe_card(recipe)
                        result['recipe'] = "\n\n".join(recipe_cards)
                    else:
                        self.logger.info(f"No recipe could be extracted from video {video_id}")
                else:
                    self.logger.info(f"No recipe content detected in video {video_id}")
            except Exception as e:
                self.logger.error(f"Error processing recipe content: {str(e)}")
            
            return result

        except Exception as e:
            self.logger.error(f"Unexpected error in get_transcript: {str(e)}")
            return None
    
    def format_duration(self, duration: str) -> str:
        """Convert YouTube duration format to readable format.
        
        Args:
            duration: Duration in YouTube format (PT1H2M10S)
            
        Returns:
            str: Formatted duration string
        """
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return "Unknown duration"
            
        hours, minutes, seconds = match.groups()
        parts = []
        
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)
    
    async def create_summary(self, transcript: str, video_details: Dict, detailed: bool) -> str:
        """Generate a summary of the video using DeepSeek's API."""
        try:
            # System prompt with Discord formatting guidance
            system_prompt = (
                "You are a helpful assistant that creates clear and informative video summaries. "
                "Format your summary using Discord-compatible markdown:\n"
                "- Use # for main titles, ## for section headers, ### for subsection headers (with a space after #)\n"
                "- Use **bold** for emphasis and important points\n"
                "- Use *italics* or _italics_ for emphasis\n"
                "- Use - for bullet points, with 2 spaces before - for nested bullets\n"
                "- Use 1., 2., etc. for ordered lists\n"
                "- Use `code` for technical terms\n"
                "\n"
                "Do not use more than 3 hashtags (####, #####) as they don't render in Discord."
            )
            
            # Create prompt based on detail level
            if detailed:
                prompt = (
                    f"Please provide a detailed summary of this video titled '{video_details['title']}' "
                    f"by {video_details['channel']}. Include key points with their timestamps:\n\n{transcript}"
                )
            else:
                prompt = (
                    f"Please provide a concise summary of this video titled '{video_details['title']}' "
                    f"by {video_details['channel']}. Focus on the main points:\n\n{transcript}"
                )

            # Configure DeepSeek API
            openai.api_key = self.deepseek_api_key
            openai.api_base = "https://api.deepseek.com"

            # Get summary from DeepSeek
            response = await openai.ChatCompletion.acreate(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000 if detailed else 500,
                temperature=0.7
            )

            summary = response.choices[0].message.content.strip()
            
            # Apply Discord formatting fixes
            return fix_discord_formatting(summary)

        except Exception as e:
            self.logger.error(f"Error creating summary: {str(e)}")
            raise

    async def is_recipe_video(self, url: str) -> bool:
        """Check if video likely contains a recipe based on title and description."""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return False

            # Get video info
            video_info = await self.get_video_details(url)
            if not video_info:
                return False

            # Check title for recipe indicators
            title = video_info['title'].lower()
            recipe_indicators = [
                'recipe', 'cooking', 'baking', 'how to make', 'how to cook',
                'tutorial', 'guide', 'step by step', 'ingredients', 'instructions'
            ]
            
            return any(indicator in title for indicator in recipe_indicators)

        except Exception as e:
            self.logger.error(f"Error checking if recipe video: {str(e)}")
            return False 