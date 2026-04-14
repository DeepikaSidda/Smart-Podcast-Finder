import json

from temporalio import activity

from app.config import settings
from models.schemas import (
    ExtractedInterests,
    ExtractInterestsRequest,
    RankRequest,
    RankResult,
    SummaryRequest,
    SummaryResult,
    VideoRecommendation,
)

EXTRACT_PROMPT = """You are an interest parser. Given a raw user interests string,
extract specific keywords and broader topic categories.
Keywords: specific terms the user mentioned (e.g. "kubernetes", "RAG", "temporal").
Topics: broader categories (e.g. "cloud infrastructure", "AI/ML", "devops").

Return ONLY valid JSON in this exact format, no other text:
{"keywords": ["keyword1", "keyword2"], "topics": ["topic1", "topic2"]}"""

RANK_PROMPT = """You are a podcast episode recommendation engine that scores long-form YouTube videos for a specific listener.

You receive rich metadata per episode: title, description, tags, chapters, view/like/comment counts, duration, and when available, transcript excerpts. Use ALL signals:
- Transcripts are the STRONGEST signal — they reveal exactly what was discussed
- Chapters reveal depth and breadth of topics
- Tags reveal exact topics and guest names
- High like-to-view ratio indicates engaging content

Scoring guide:
- 85-100: Episode directly covers a user keyword — confirmed by transcript, chapters, tags, or title
- 70-84: Strong topical overlap, likely valuable discussion
- 50-69: Adjacent topic a curious listener would enjoy
- 30-49: Weak connection
- 0-29: Completely unrelated

Rules:
- ONLY use videos from the provided list — never invent episodes
- Copy the EXACT title, URL, duration, and views from the input
- Every video MUST appear in output — rank ALL of them
- Sort by score descending
- In "why", mention what makes this episode valuable

Return ONLY valid JSON in this exact format, no other text:
{"recommendations": [{"title": "exact title", "url": "exact url", "score": 85, "why": "reason", "duration": "duration", "views": 12345}]}"""

SUMMARY_PROMPT = """You are a podcast channel analyst specializing in YouTube long-form content.
Given a channel name, its episode catalog, and when available, transcript excerpts, produce:
1. A brief summary of the podcast's focus and format (2-3 sentences)
2. 3-5 key insights (recurring themes, discussion depth, standout content)
3. The content tone: educational, entertainment, news, tutorial, or mixed

Return ONLY valid JSON in this exact format, no other text:
{"summary": "channel summary here", "key_insights": ["insight1", "insight2", "insight3"], "tone": "educational"}"""


def _call_bedrock(system_prompt: str, user_prompt: str) -> str:
    """Call AWS Bedrock with Llama model."""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)

    # Llama prompt format
    full_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    body = json.dumps({
        "prompt": full_prompt,
        "max_gen_len": 4096,
        "temperature": 0.2,
    })

    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    return result.get("generation", "")


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Google Gemini."""
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=45_000),
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )
    return response.text


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Route to the configured LLM provider."""
    if settings.llm_provider == "bedrock":
        return _call_bedrock(system_prompt, user_prompt)
    return _call_gemini(system_prompt, user_prompt)


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return json.loads(text)


@activity.defn
async def extract_interests(request: ExtractInterestsRequest) -> ExtractedInterests:
    """Parse raw interests string into structured keywords + topics."""
    activity.logger.info(f"Extracting interests from: {request.interests[:80]}")

    response = _call_llm(EXTRACT_PROMPT, f"User interests: {request.interests}")
    data = _extract_json(response)

    result = ExtractedInterests(
        keywords=data.get("keywords", []),
        topics=data.get("topics", []),
    )
    activity.logger.info(f"Extracted {len(result.keywords)} keywords, {len(result.topics)} topics")
    return result


@activity.defn
async def rank_videos(request: RankRequest) -> RankResult:
    """Rank videos by relevance to structured interests."""
    video_lines = []
    for i, v in enumerate(request.videos, 1):
        parts = [
            f"[{i}] {v.title}",
            f"    URL: {v.url} | Duration: {v.duration} | Views: {v.views} | Likes: {v.likes} | Comments: {v.comments} | Date: {v.date}",
            f"    Description: {v.description[:500]}",
        ]
        if v.tags:
            parts.append(f"    Tags: {', '.join(v.tags[:12])}")
        if v.chapters:
            parts.append(f"    Chapters: {', '.join(v.chapters[:10])}")
        transcript = request.transcripts.get(v.url, "")
        if transcript:
            parts.append(f"    Transcript excerpt: {transcript[:800]}")
        video_lines.append("\n".join(parts))
    videos_text = "\n\n".join(video_lines)

    prompt = f"""Listener keywords: {', '.join(request.keywords)}
Listener topics: {', '.join(request.topics)}

{len(request.videos)} podcast episodes from the channel:

{videos_text}

Score and rank ALL {len(request.videos)} episodes for this listener. Return every episode with a score."""

    activity.logger.info(f"Ranking {len(request.videos)} videos with {settings.llm_provider}")
    response = _call_llm(RANK_PROMPT, prompt)
    data = _extract_json(response)

    recs = []
    for r in data.get("recommendations", []):
        try:
            recs.append(VideoRecommendation(
                title=r["title"],
                url=r["url"],
                score=min(100, max(0, int(r.get("score", 50)))),
                why=r.get("why", ""),
                duration=r.get("duration", ""),
                views=int(r.get("views", 0)),
            ))
        except (KeyError, ValueError) as e:
            activity.logger.warning(f"Skipping malformed recommendation: {e}")

    return RankResult(recommendations=sorted(recs, key=lambda x: x.score, reverse=True))


@activity.defn
async def generate_summary(request: SummaryRequest) -> SummaryResult:
    """Generate channel overview, insights, and tone analysis."""
    titles = [v.title for v in request.videos]
    titles_text = "\n".join(f"- {t}" for t in titles)

    transcript_section = ""
    for v in request.videos:
        transcript = request.transcripts.get(v.url, "")
        if transcript:
            transcript_section += f"\n--- {v.title} ---\n{transcript[:500]}\n"

    transcript_prompt = ""
    if transcript_section:
        transcript_prompt = f"\n\nTranscript excerpts from select episodes:{transcript_section}"

    prompt = f"""Channel: {request.channel_name}
User interest keywords: {', '.join(request.keywords)}

Recent video titles:
{titles_text}{transcript_prompt}

Analyze this channel."""

    activity.logger.info(f"Generating summary for {request.channel_name}")
    response = _call_llm(SUMMARY_PROMPT, prompt)
    data = _extract_json(response)

    valid_tones = {"educational", "entertainment", "news", "tutorial", "mixed"}
    tone = data.get("tone", "mixed").lower()
    if tone not in valid_tones:
        tone = "mixed"

    return SummaryResult(
        summary=data.get("summary", ""),
        key_insights=data.get("key_insights", []),
        tone=tone,
    )
