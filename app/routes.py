import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from temporalio.client import WorkflowFailureError
from temporalio.service import RPCError

from models.schemas import (
    AnalyzeRequestAPI,
    DeepDiveInput,
    DeepDiveRequestAPI,
    DeepDiveResult,
    StartResponse,
    StatusResponse,
    WorkflowInput,
    WorkflowResult,
    WorkflowStatus,
)
from workflows.deep_dive import DeepDiveWorkflow
from workflows.insights import PodcastInsightsWorkflow

router = APIRouter(prefix="/api", tags=["insights"])


@router.post("/analyze", response_model=StartResponse)
async def start_analysis(request: Request, body: AnalyzeRequestAPI) -> StartResponse:
    client = request.app.state.temporal_client
    wf_id = f"insights-{uuid.uuid4().hex[:8]}"

    await client.start_workflow(
        PodcastInsightsWorkflow.run,
        WorkflowInput(
            channel_query=body.channel_query,
            interests=body.interests,
            max_videos=body.max_videos,
            provider=body.provider,
        ),
        id=wf_id,
        task_queue=request.app.state.task_queue,
        execution_timeout=timedelta(minutes=5),
    )
    return StartResponse(workflow_id=wf_id)


@router.get("/status/{workflow_id}", response_model=StatusResponse)
async def get_status(request: Request, workflow_id: str) -> StatusResponse:
    client = request.app.state.temporal_client
    handle = client.get_workflow_handle(workflow_id)
    try:
        status: WorkflowStatus = await handle.query(PodcastInsightsWorkflow.get_status)
        return StatusResponse(
            workflow_id=workflow_id,
            phase=status.phase,
            detail=status.detail,
        )
    except RPCError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        # Workflow may be initializing or temporarily unavailable
        return StatusResponse(
            workflow_id=workflow_id,
            phase="searching",
            detail="Initializing workflow...",
        )


@router.get("/result/{workflow_id}", response_model=WorkflowResult)
async def get_result(request: Request, workflow_id: str) -> WorkflowResult:
    client = request.app.state.temporal_client
    handle = client.get_workflow_handle(workflow_id)
    try:
        result = await handle.result()
        return WorkflowResult(workflow_id=workflow_id, **result)
    except WorkflowFailureError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RPCError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Deep Dive endpoints ---

@router.post("/deep-dive", response_model=StartResponse)
async def start_deep_dive(request: Request, body: DeepDiveRequestAPI) -> StartResponse:
    client = request.app.state.temporal_client
    wf_id = f"deepdive-{uuid.uuid4().hex[:8]}"

    await client.start_workflow(
        DeepDiveWorkflow.run,
        DeepDiveInput(
            video_url=body.video_url,
            video_title=body.video_title,
            interests=body.interests,
        ),
        id=wf_id,
        task_queue=request.app.state.task_queue,
        execution_timeout=timedelta(minutes=3),
    )
    return StartResponse(workflow_id=wf_id)


@router.get("/deep-dive/status/{workflow_id}")
async def get_deep_dive_status(request: Request, workflow_id: str):
    client = request.app.state.temporal_client
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(DeepDiveWorkflow.get_status)
        return {"workflow_id": workflow_id, "phase": status.phase, "detail": status.detail}
    except Exception:
        return {"workflow_id": workflow_id, "phase": "analyzing", "detail": "Processing..."}


@router.get("/deep-dive/result/{workflow_id}", response_model=DeepDiveResult)
async def get_deep_dive_result(request: Request, workflow_id: str) -> DeepDiveResult:
    client = request.app.state.temporal_client
    handle = client.get_workflow_handle(workflow_id)
    try:
        result = await handle.result()
        return DeepDiveResult(**result)
    except WorkflowFailureError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RPCError as e:
        raise HTTPException(status_code=404, detail=str(e))
