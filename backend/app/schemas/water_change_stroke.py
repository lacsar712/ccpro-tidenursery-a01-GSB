from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WaterChangeStrokeCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    out_volume_m3: float = Field(..., gt=0, alias="outVolumeM3")
    in_volume_m3: float = Field(..., gt=0, alias="inVolumeM3")
    started_at: datetime = Field(..., alias="startedAt")
    operator_name: str = Field(..., min_length=1, max_length=64, alias="operatorName")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class WaterChangeStrokeFinish(BaseModel):
    ended_at: datetime = Field(..., alias="endedAt")

    model_config = ConfigDict(populate_by_name=True)


class WaterChangeStrokeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    out_volume_m3: float = Field(serialization_alias="outVolumeM3")
    in_volume_m3: float = Field(serialization_alias="inVolumeM3")
    started_at: datetime = Field(serialization_alias="startedAt")
    ended_at: Optional[datetime] = Field(None, serialization_alias="endedAt")
    operator_name: str = Field(serialization_alias="operatorName")
    notes: Optional[str] = None
