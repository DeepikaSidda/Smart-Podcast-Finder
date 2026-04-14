import re
from dataclasses import dataclass, field

from temporalio import activity
from youtube_transcript_api import YouTubeTranscriptApi

from models.schemas import VideoMetadata


@dataclass
class TranscriptRequest:
    videos: list[VideoMetadata] = field(default_factory=list)


@dataclass
class VideoTranscript:
    url: str
    title: str
    transcript_text: str = ""
    has_transcript: bool = False


@dataclass
class TranscriptResult:
    transcripts: list[VideoTranscript] = field(default_factory=list)


def _extract_video_id(url: str) -> str | None:
    """Extract video ID from YouTube URL."""
    m = re.search(r"[?&]v=([^&]+)", url)
    return m.group(1) if m else None


@activity.defn
async def fetch_transcripts(request: TranscriptRequest) -> TranscriptResult:
    """Fetch transcripts for a list of YouTube videos."""
    results = []
    ytt_api = YouTubeTranscriptApi()

    for video in request.videos:
        video_id = _extract_video_id(video.url)
        if not video_id:
            results.append(VideoTranscript(url=video.url, title=video.title))
            continue

        try:
            transcript = ytt_api.fetch(video_id, languages=["en", "en-US", "en-GB", "hi"])
            # Join all text snippets, limit to ~2000 chars for LLM context
            full_text = " ".join(snippet.text for snippet in transcript.snippets)
            # Truncate to keep LLM context manageable
            truncated = full_text[:2000]
            results.append(VideoTranscript(
                url=video.url,
                title=video.title,
                transcript_text=truncated,
                has_transcript=True,
            ))
            activity.logger.info(f"Got transcript for: {video.title[:50]} ({len(full_text)} chars)")
        except Exception as e:
            activity.logger.warning(f"No transcript for '{video.title[:50]}': {e}")
            results.append(VideoTranscript(url=video.url, title=video.title))

    got = sum(1 for t in results if t.has_transcript)
    activity.logger.info(f"Fetched {got}/{len(results)} transcripts")
    return TranscriptResult(transcripts=results)
