"""
Runtime Intent Inference Engine for Custom ML Model.
Loads versioned model artifacts and executes calibrated predictions with confidence thresholds.
Flags ambiguous predictions to ensure safety before executing system actions.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import joblib
from pydantic import BaseModel, Field

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class IntentPrediction(BaseModel):
    intent: str
    confidence: float
    is_ambiguous: bool = False
    top_intents: List[Dict[str, Any]] = Field(default_factory=list)
    model_version: str = "1.0.0"
    raw_text: str = ""


class IntentInferenceEngine:
    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or settings.active_intent_model_dir
        self.model = None
        self.metadata = {}
        self.classes: List[str] = []
        self._load_model()

    def _load_model(self):
        """Loads serialized model pipeline and metadata."""
        model_file = self.model_dir / "model.joblib"
        meta_file = self.model_dir / "metadata.json"

        if model_file.exists() and meta_file.exists():
            try:
                self.model = joblib.load(model_file)
                with open(meta_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                self.classes = self.metadata.get("classes", [])
                logger.info(f"Loaded ML Intent Model v{self.metadata.get('version')} from {self.model_dir}")
            except Exception as e:
                logger.error(f"Failed to load ML model from {self.model_dir}: {e}")
                self.model = None
        else:
            logger.warning(f"No ML model found at {self.model_dir}. Running in heuristic fallback mode.")

    def predict(self, text: str) -> IntentPrediction:
        """
        Executes calibrated inference on user text.
        Applies confidence threshold (0.65) and ambiguity delta check (0.15).
        """
        clean_text = text.strip()
        if not clean_text:
            return IntentPrediction(
                intent="UNKNOWN",
                confidence=0.0,
                is_ambiguous=True,
                raw_text=""
            )

        if self.model is None:
            # Fallback heuristic
            return self._heuristic_prediction(clean_text)

        try:
            probs = self.model.predict_proba([clean_text])[0]
            classes = self.model.classes_ if hasattr(self.model, "classes_") else self.classes

            # Pair and sort by probability descending
            ranked = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
            top_intent, top_conf = ranked[0]
            top_conf = float(top_conf)

            # Check ambiguity: low confidence OR top 2 are very close
            second_conf = float(ranked[1][1]) if len(ranked) > 1 else 0.0
            is_ambiguous = (
                top_conf < settings.ml_intent_confidence_threshold or
                (top_conf - second_conf) < settings.ml_ambiguity_delta_threshold
            )

            top_intents_list = [
                {"intent": str(name), "confidence": round(float(prob), 4)}
                for name, prob in ranked[:3]
            ]

            return IntentPrediction(
                intent=str(top_intent),
                confidence=round(top_conf, 4),
                is_ambiguous=is_ambiguous,
                top_intents=top_intents_list,
                model_version=self.metadata.get("version", "1.0.0"),
                raw_text=clean_text
            )
        except Exception as e:
            logger.error(f"Inference error on text '{clean_text}': {e}")
            return self._heuristic_prediction(clean_text)

    def _heuristic_prediction(self, text: str) -> IntentPrediction:
        """Fallback prediction when ML model artifact is unavailable."""
        lower = text.lower()
        if any(w in lower for w in ["call", "phone", "dial"]):
            intent = "CALL_CONTACT"
        elif any(w in lower for w in ["whatsapp", "message", "text"]):
            intent = "SEND_WHATSAPP_MESSAGE"
        elif any(w in lower for w in ["search web", "google", "look up"]):
            intent = "SEARCH_WEB"
        elif any(w in lower for w in ["find", "resume", "pdf", "file"]):
            intent = "SEARCH_FILE"
        elif "folder" in lower and any(w in lower for w in ["create", "make", "banao"]):
            intent = "CREATE_FOLDER"
        elif any(w in lower for w in ["open", "launch", "start"]):
            intent = "OPEN_APPLICATION"
        else:
            intent = "OPEN_APPLICATION"

        return IntentPrediction(
            intent=intent,
            confidence=0.5,
            is_ambiguous=True,
            top_intents=[{"intent": intent, "confidence": 0.5}],
            model_version="heuristic-fallback",
            raw_text=text
        )


intent_inference_engine = IntentInferenceEngine()
