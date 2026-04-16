import asyncio

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from activities.analyzer import extract_interests, generate_summary, rank_videos, deep_dive_episode
from activities.scraper import search_youtube
from activities.spotify import search_spotify
from activities.transcript import fetch_transcripts
from app.config import settings
from workflows.deep_dive import DeepDiveWorkflow
from workflows.insights import PodcastInsightsWorkflow


async def main():
    client = await Client.connect(
        settings.temporal_host,
        data_converter=pydantic_data_converter,
    )
    worker = Worker(
        client,
        task_queue=settings.task_queue,
        workflows=[PodcastInsightsWorkflow, DeepDiveWorkflow],
        activities=[search_youtube, search_spotify, extract_interests, rank_videos, generate_summary, fetch_transcripts, deep_dive_episode],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules()
        ),
    )
    print(f"Worker listening on '{settings.task_queue}' — Ctrl+C to stop")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
