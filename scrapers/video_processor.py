import os
import logging
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
import requests
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

class YouTubeProcessor:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key) if self.api_key else None

    def get_trending_ai_videos(self, max_results: int = 5) -> list:
        """Obtiene videos trending de canales de IA"""
        if not self.youtube:
            logging.warning("YouTube API no configurada")
            return []

        try:
            # Buscar videos de IA/tecnología
            search_response = self.youtube.search().list(
                q="artificial intelligence machine learning AI",
                part="snippet",
                type="video",
                maxResults=max_results,
                order="date",
                relevanceLanguage="en"
            ).execute()

            videos = []
            for item in search_response.get('items', []):
                video_data = {
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'video_id': item['id']['videoId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                }
                videos.append(video_data)

            logging.info(f"Encontrados {len(videos)} videos de IA")
            return videos

        except Exception as e:
            logging.error(f"Error obteniendo videos de YouTube: {e}")
            return []

    def get_video_transcript(self, video_id: str) -> Optional[str]:
        """Obtiene el transcript del video usando youtube-transcript-api."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = " ".join([entry['text'] for entry in transcript_list])
            logging.info(f"Transcript obtenido para el video {video_id}")
            return transcript
        except NoTranscriptFound:
            logging.warning(f"No se encontró transcript para el video {video_id}. Intentando con la descripción.")
            try:
                video_response = self.youtube.videos().list(
                    part="snippet",
                    id=video_id
                ).execute()
                if video_response['items']:
                    return video_response['items'][0]['snippet']['description']
            except Exception as e:
                logging.error(f"Error obteniendo descripción del video {video_id}: {e}")
        except Exception as e:
            logging.error(f"Error obteniendo transcript para el video {video_id}: {e}")
        return None

# Fuentes de video predefinidas
YOUTUBE_SOURCES = [
    {
        "type": "youtube_channel",
        "name": "Two Minute Papers",
        "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
        "category": "ai_research"
    },
    {
        "type": "youtube_channel",
        "name": "AI Explained",
        "channel_id": "UCmI3Vg9O7Spd2YKtR1qtnDw",
        "category": "ai_news"
    },
    {
        "type": "youtube_channel",
        "name": "Lex Fridman",
        "channel_id": "UCSHZKyawb77ixDdsGog4iWA",
        "category": "ai_interviews"
    }
]
