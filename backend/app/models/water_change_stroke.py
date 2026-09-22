from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WaterChangeStroke(Base):
    """换水冲程：挂塘口，进行中（end_at 为空）时与投喂互斥。"""

    __tablename__ = "water_change_strokes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(ForeignKey("ponds.id"), nullable=False, index=True)
    outflow_m3: Mapped[float] = mapped_column(Float, nullable=False)
    inflow_m3: Mapped[float] = mapped_column(Float, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_name: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 结束冲程时同事务追加的水质样；为空说明冲程尚未完成结束流程
    closing_sample_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("water_samples.id"), nullable=True
    )

    pond: Mapped["Pond"] = relationship("Pond", back_populates="water_change_strokes")
