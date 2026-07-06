"""
ReplenishmentInferenceService — model loading and feature construction.

Separating inference logic from the FastAPI router keeps main.py clean
and makes this class independently unit-testable without starting a server.
"""

import logging
from typing import List

import joblib
import pandas as pd

from schemas import ReplenishmentRequest, ReplenishmentResponse

logger = logging.getLogger(__name__)


class ReplenishmentInferenceService:
    """
    Loads the XGBoost model artifact once and exposes a predict() method.

    Feature construction:
        Incoming requests use clean string fields (store_id, temp_zone).
        This class one-hot encodes them to match the exact training schema,
        then uses reindex() to guard against any column mismatch.
    """

    STORE_IDS = ["DS-BLR-01", "DS-BLR-02", "DS-BLR-03"]
    TEMP_ZONES = ["Ambient", "Chilled", "Frozen"]

    def __init__(self, model_path: str):
        self._model = joblib.load(model_path)
        self.expected_features: List[str] = self._model.get_booster().feature_names
        logger.info(
            f"[InferenceService] Loaded model from '{model_path}'. "
            f"Expected features: {self.expected_features}"
        )

    def _build_feature_row(self, request: ReplenishmentRequest) -> pd.DataFrame:
        """
        Converts a ReplenishmentRequest into a single-row DataFrame
        matching the model's training feature schema exactly.
        """
        row = {
            "On_Hand": request.on_hand,
            "Reserved": request.reserved,
            "Daily_Velocity": request.daily_velocity,
        }

        # One-hot encode store_id
        for store in self.STORE_IDS:
            row[f"Dark_Store_ID_{store}"] = int(request.store_id == store)

        # One-hot encode temp_zone
        for zone in self.TEMP_ZONES:
            row[f"Temp_Zone_{zone}"] = int(request.temp_zone == zone)

        # Align to training schema — drops unknowns, fills missing with 0
        df = pd.DataFrame([row]).reindex(columns=self.expected_features, fill_value=0)
        return df

    def predict(self, request: ReplenishmentRequest) -> ReplenishmentResponse:
        """
        Runs inference and returns a structured ReplenishmentResponse.
        """
        df = self._build_feature_row(request)

        prediction = int(self._model.predict(df)[0])
        confidence = round(float(self._model.predict_proba(df)[0][1]), 4)
        urgent = prediction == 1

        logger.info(
            f"[InferenceService] SKU={request.sku_id} Store={request.store_id} "
            f"Prediction={prediction} Confidence={confidence}"
        )

        return ReplenishmentResponse(
            sku_id=request.sku_id,
            store_id=request.store_id,
            urgent_reorder=urgent,
            confidence_score=confidence,
            action="GENERATE_PURCHASE_ORDER" if urgent else "NO_ACTION_REQUIRED",
        )
