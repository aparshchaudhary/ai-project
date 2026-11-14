"""
User Feedback & Continuous Improvement Service.
Captures user-confirmed corrections and execution ratings.
Stores feedback securely in data/ml/user_feedback.json for shadow evaluation and gated retraining.
"""

from __future__ import annotations
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class UserCorrection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_utterance: str
    predicted_intent: str
    corrected_intent: str
    confidence: float
    is_ambiguous: bool = False
    verified_by_user: bool = True
    context: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class FeedbackService:
    def __init__(self, feedback_file: Optional[Path] = None):
        self.feedback_file = feedback_file or settings.user_feedback_file
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_feedback_file()

    def _ensure_feedback_file(self):
        if not self.feedback_file.exists():
            with open(self.feedback_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def record_correction(
        self,
        raw_utterance: str,
        predicted_intent: str,
        corrected_intent: str,
        confidence: float,
        is_ambiguous: bool = False,
        verified_by_user: bool = True,
        context: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> UserCorrection:
        """Records an approved user correction for future retraining."""
        correction = UserCorrection(
            raw_utterance=raw_utterance.strip(),
            predicted_intent=predicted_intent.strip(),
            corrected_intent=corrected_intent.strip(),
            confidence=round(confidence, 4),
            is_ambiguous=is_ambiguous,
            verified_by_user=verified_by_user,
            context=context or {},
            notes=notes
        )

        entries = self.load_feedback()
        entries.append(correction.model_dump())

        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Logged user correction [{correction.id}]: '{raw_utterance}' -> {corrected_intent} "
            f"(predicted: {predicted_intent}, conf: {confidence:.2f})"
        )
        return correction

    def load_feedback(self) -> List[Dict[str, Any]]:
        """Loads all recorded feedback entries."""
        if not self.feedback_file.exists():
            return []
        try:
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading feedback file {self.feedback_file}: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Returns summary statistics of collected feedback."""
        entries = self.load_feedback()
        total = len(entries)
        verified = sum(1 for e in entries if e.get("verified_by_user", False))
        
        intent_corrections = {}
        for e in entries:
            c = e.get("corrected_intent")
            if c:
                intent_corrections[c] = intent_corrections.get(c, 0) + 1

        return {
            "total_feedback_count": total,
            "verified_count": verified,
            "corrections_by_target_intent": intent_corrections,
            "threshold_for_retrain": settings.retrain_feedback_threshold,
            "ready_for_retrain": verified >= settings.retrain_feedback_threshold
        }


feedback_service = FeedbackService()
