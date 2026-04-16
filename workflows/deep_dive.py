from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.analyzer import deep_dive_episode
    from models.schemas import DeepDiveInput, DeepDiveStatus

RETRY = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
)


@workflow.defn
class DeepDiveWorkflow:
    def __init__(self) -> None:
        self._status = DeepDiveStatus("queued")

    @workflow.run
    async def run(self, input: DeepDiveInput) -> dict:
        self._status = DeepDiveStatus("analyzing", f"Analyzing: {input.video_title[:50]}")

        result = await workflow.execute_activity(
            deep_dive_episode,
            input.video_url,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RETRY,
        )

        result["video_title"] = input.video_title
        result["video_url"] = input.video_url
        self._status = DeepDiveStatus("completed", "Deep dive complete")
        return result

    @workflow.query
    def get_status(self) -> DeepDiveStatus:
        return self._status
