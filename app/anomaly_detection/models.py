from datetime import datetime

from pydantic import BaseModel


class MetricSample(BaseModel):
    metric_name: str
    value: float
    timestamp: datetime


class AnomalyResult(BaseModel):
    metric_name: str
    anomaly_score: float
    detection_method: str
    timestamp: datetime
    metadata: dict = {}