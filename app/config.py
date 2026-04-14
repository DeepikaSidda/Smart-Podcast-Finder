from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env"}

    gemini_api_key: str = ""
    youtube_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    temporal_host: str = "localhost:7233"
    task_queue: str = "podcast-insights"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    llm_provider: str = "bedrock"  # "gemini" or "bedrock"
    bedrock_model_id: str = "us.meta.llama3-3-70b-instruct-v1:0"
    bedrock_region: str = "us-east-1"


settings = Settings()
