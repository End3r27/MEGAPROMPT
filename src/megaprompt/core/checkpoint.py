"""Checkpoint system for saving and resuming pipeline execution."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from megaprompt.schemas.assembly import MegaPrompt
from megaprompt.schemas.constraints import Constraints
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis


class Checkpoint:
    """Represents a checkpoint of pipeline execution."""

    def __init__(
        self,
        checkpoint_id: str,
        timestamp: datetime,
        input_hash: str,
        stage: str,
        intent: Optional[IntentExtraction] = None,
        decomposition: Optional[ProjectDecomposition] = None,
        expansion: Optional[DomainExpansion] = None,
        risk_analysis: Optional[RiskAnalysis] = None,
        constraints: Optional[Constraints] = None,
        error: Optional[str] = None,
    ):
        """Initialize checkpoint."""
        self.checkpoint_id = checkpoint_id
        self.timestamp = timestamp
        self.input_hash = input_hash
        self.stage = stage
        self.intent = intent
        self.decomposition = decomposition
        self.expansion = expansion
        self.risk_analysis = risk_analysis
        self.constraints = constraints
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary."""
        data = {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "input_hash": self.input_hash,
            "stage": self.stage,
        }

        if self.intent:
            data["intent"] = self.intent.model_dump()
        if self.decomposition:
            data["decomposition"] = self.decomposition.model_dump()
        if self.expansion:
            data["expansion"] = self.expansion.model_dump()
        if self.risk_analysis:
            data["risk_analysis"] = self.risk_analysis.model_dump()
        if self.constraints:
            data["constraints"] = self.constraints.model_dump()
        if self.error:
            data["error"] = self.error

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        checkpoint = cls(
            checkpoint_id=data["checkpoint_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            input_hash=data["input_hash"],
            stage=data["stage"],
        )

        if "intent" in data:
            checkpoint.intent = IntentExtraction.model_validate(data["intent"])
        if "decomposition" in data:
            checkpoint.decomposition = ProjectDecomposition.model_validate(
                data["decomposition"]
            )
        if "expansion" in data:
            checkpoint.expansion = DomainExpansion.model_validate(data["expansion"])
        if "risk_analysis" in data:
            checkpoint.risk_analysis = RiskAnalysis.model_validate(
                data["risk_analysis"]
            )
        if "constraints" in data:
            checkpoint.constraints = Constraints.model_validate(data["constraints"])
        if "error" in data:
            checkpoint.error = data["error"]

        return checkpoint

    def save(self, checkpoint_dir: Path) -> Path:
        """Save checkpoint to file."""
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoint_dir / f"{self.checkpoint_id}.json"
        checkpoint_file.write_text(
            json.dumps(self.to_dict(), indent=2), encoding="utf-8"
        )
        return checkpoint_file


class CheckpointManager:
    """Manages checkpoints for pipeline execution."""

    def __init__(self, checkpoint_dir: Path):
        """Initialize checkpoint manager."""
        self.checkpoint_dir = checkpoint_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _hash_input(self, input_text: str) -> str:
        """Generate hash for input text."""
        import hashlib

        return hashlib.sha256(input_text.encode("utf-8")).hexdigest()[:16]

    def create_checkpoint(
        self,
        input_text: str,
        stage: str,
        intent: Optional[IntentExtraction] = None,
        decomposition: Optional[ProjectDecomposition] = None,
        expansion: Optional[DomainExpansion] = None,
        risk_analysis: Optional[RiskAnalysis] = None,
        constraints: Optional[Constraints] = None,
        error: Optional[str] = None,
    ) -> Checkpoint:
        """Create and save a checkpoint."""
        input_hash = self._hash_input(input_text)
        checkpoint_id = f"{input_hash}_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            input_hash=input_hash,
            stage=stage,
            intent=intent,
            decomposition=decomposition,
            expansion=expansion,
            risk_analysis=risk_analysis,
            constraints=constraints,
            error=error,
        )

        checkpoint.save(self.checkpoint_dir)
        return checkpoint

    def find_latest_checkpoint(self, input_text: str) -> Optional[Checkpoint]:
        """Find the latest checkpoint for given input."""
        input_hash = self._hash_input(input_text)

        # Find all checkpoints for this input
        checkpoints = []
        for checkpoint_file in self.checkpoint_dir.glob(f"{input_hash}_*.json"):
            try:
                data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                checkpoint = Checkpoint.from_dict(data)
                checkpoints.append(checkpoint)
            except Exception:
                continue

        if not checkpoints:
            return None

        # Return the most recent checkpoint
        return max(checkpoints, key=lambda c: c.timestamp)

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints."""
        checkpoints = []
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                checkpoint = Checkpoint.from_dict(data)
                checkpoints.append(checkpoint)
            except Exception:
                continue

        return sorted(checkpoints, key=lambda c: c.timestamp, reverse=True)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint by ID."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        return False

    def clear_checkpoints(self, input_hash: Optional[str] = None) -> int:
        """Clear checkpoints, optionally filtered by input hash."""
        deleted = 0
        pattern = f"{input_hash}_*.json" if input_hash else "*.json"
        for checkpoint_file in self.checkpoint_dir.glob(pattern):
            try:
                checkpoint_file.unlink()
                deleted += 1
            except Exception:
                pass
        return deleted

