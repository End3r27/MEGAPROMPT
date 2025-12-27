"""API views for MEGAPROMPT web interface."""

import threading
import uuid
from pathlib import Path

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from api.serializers import (
    GenerateRequestSerializer,
    GenerateResponseSerializer,
    GenerateResultSerializer,
    AnalyzeRequestSerializer,
    AnalyzeResponseSerializer,
    AnalyzeResultSerializer,
    ConfigSerializer,
)
from core.services import MegaPromptService

# In-memory job storage (for local use)
_jobs = {}
_jobs_lock = threading.Lock()


def _run_generate_job(job_id: str, prompt: str, config: dict):
    """Run generate job in background thread."""
    try:
        result_text, intermediate_outputs = MegaPromptService.generate_prompt(prompt, config)
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "completed",
                "result": result_text,
                "intermediate_outputs": intermediate_outputs,
                "error": None,
            }
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "failed",
                "result": None,
                "intermediate_outputs": None,
                "error": str(e),
            }


def _run_analyze_job(job_id: str, codebase_path: str, config: dict, mode: str):
    """Run analyze job in background thread."""
    try:
        result = MegaPromptService.analyze_codebase(codebase_path, config, mode)
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "completed",
                "result": result,
                "error": None,
            }
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "failed",
                "result": None,
                "error": str(e),
            }


@api_view(["POST"])
def generate(request):
    """Start a generate job."""
    serializer = GenerateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    job_id = str(uuid.uuid4())

    # Initialize job
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "result": None, "error": None}

    # Start background thread
    thread = threading.Thread(
        target=_run_generate_job,
        args=(job_id, data["prompt"], data),
        daemon=True,
    )
    thread.start()

    response_serializer = GenerateResponseSerializer(
        {
            "job_id": job_id,
            "status": "running",
            "message": "Generation started",
        }
    )
    return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
def get_generate_result(request, job_id: str):
    """Get generate job result."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

    result_serializer = GenerateResultSerializer(
        {
            "job_id": job_id,
            "status": job["status"],
            "result": job.get("result"),
            "intermediate_outputs": job.get("intermediate_outputs"),
            "error": job.get("error"),
        }
    )
    return Response(result_serializer.data)


@api_view(["POST"])
def analyze(request):
    """Start an analyze job."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    codebase_path = data.get("codebase_path")
    if not codebase_path:
        return Response({"error": "codebase_path is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate path
    path = Path(codebase_path)
    if not path.exists() or not path.is_dir():
        return Response({"error": "Invalid codebase path"}, status=status.HTTP_400_BAD_REQUEST)

    job_id = str(uuid.uuid4())

    # Initialize job
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "result": None, "error": None}

    # Start background thread
    thread = threading.Thread(
        target=_run_analyze_job,
        args=(job_id, codebase_path, data, data.get("mode", "full")),
        daemon=True,
    )
    thread.start()

    response_serializer = AnalyzeResponseSerializer(
        {
            "job_id": job_id,
            "status": "running",
            "message": "Analysis started",
        }
    )
    return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
def get_analyze_result(request, job_id: str):
    """Get analyze job result."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

    result_serializer = AnalyzeResultSerializer(
        {
            "job_id": job_id,
            "status": job["status"],
            "result": job.get("result"),
            "error": job.get("error"),
        }
    )
    return Response(result_serializer.data)


@api_view(["GET", "POST"])
def config_view(request):
    """Get or update configuration."""
    if request.method == "GET":
        config = MegaPromptService.get_config()
        serializer = ConfigSerializer(config)
        return Response(serializer.data)
    else:  # POST
        serializer = ConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        success = MegaPromptService.save_config(serializer.validated_data)
        if success:
            return Response({"message": "Configuration saved"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to save configuration"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET", "DELETE"])
def cache_view(request):
    """Get cache statistics or clear cache."""
    from megaprompt.core.cache import Cache

    cache_dir = Path.home() / ".megaprompt" / "cache"
    cache = Cache(cache_dir) if cache_dir.exists() else None

    if request.method == "GET":
        stats = {
            "cache_dir": str(cache_dir),
            "exists": cache_dir.exists(),
        }
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("**/*"))
            file_count = len([f for f in cache_files if f.is_file()])
            total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
            stats["file_count"] = file_count
            stats["total_size"] = total_size
            stats["total_size_mb"] = total_size / 1024 / 1024
        return Response(stats)
    else:  # DELETE
        if cache_dir.exists():
            import shutil

            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            return Response({"message": "Cache cleared"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Cache directory does not exist"}, status=status.HTTP_200_OK)


@api_view(["GET", "DELETE"])
def checkpoints_view(request, checkpoint_id: str = None):
    """List checkpoints or get/delete a specific checkpoint."""
    checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"

    if request.method == "GET":
        if checkpoint_id:
            # Get specific checkpoint
            checkpoint_file = checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                import json

                content = checkpoint_file.read_text(encoding="utf-8")
                data = json.loads(content)
                return Response(data)
            else:
                return Response({"error": "Checkpoint not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # List all checkpoints
            checkpoints = []
            if checkpoint_dir.exists():
                checkpoint_files = sorted(
                    checkpoint_dir.glob("*.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                for checkpoint_file in checkpoint_files:
                    import json

                    try:
                        content = checkpoint_file.read_text(encoding="utf-8")
                        data = json.loads(content)
                        checkpoints.append(
                            {
                                "id": checkpoint_file.stem,
                                "filename": checkpoint_file.name,
                                "timestamp": checkpoint_file.stat().st_mtime,
                                "data": data,
                            }
                        )
                    except Exception:
                        pass
            return Response({"checkpoints": checkpoints})
    else:  # DELETE
        if checkpoint_id:
            checkpoint_file = checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                return Response({"message": "Checkpoint deleted"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Checkpoint not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "checkpoint_id required"}, status=status.HTTP_400_BAD_REQUEST)

