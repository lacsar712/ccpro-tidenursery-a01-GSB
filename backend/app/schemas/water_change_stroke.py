from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WaterChangeStrokeCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    outflow_m3: float = Field(..., gt=0, alias="outflowM3")
    inflow_m3: float = Field(..., gt=0, alias="inflowM3")
    start_at: datetime = Field(..., alias="startAt")
    operator_name: str = Field(..., min_length=1, max_length=64, alias="operatorName")
    # 隔离塘（quarantine）开冲程时必填的备注类说明
    note: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)


class WaterChangeStrokeFinish(BaseModel):
    end_at: datetime = Field(..., alias="endAt")

    model_config = ConfigDict(populate_by_name=True)


class WaterChangeStrokeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    outflow_m3: float = Field(serialization_alias="outflowM3")
    inflow_m3: float = Field(serialization_alias="inflowM3")
    start_at: datetime = Field(serialization_alias="startAt")
    end_at: Optional[datetime] = Field(None, serialization_alias="endAt")
    operator_name: str = Field(serialization_alias="operatorName")
    note: Optional[str] = None
    # 结束冲程时同事务自动追加的水质样 id
    closing_sample_id: Optional[int] = Field(None, serialization_alias="closingSampleId")
