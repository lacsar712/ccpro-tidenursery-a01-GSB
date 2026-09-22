"""换水冲程共用规则：冲程状态判定、与投喂互斥、开始时刻半小时冲突。

投喂创建与冲程开启都调用这里的函数，保证互斥判定与冲程状态同源。
"""

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.water_change_stroke import WaterChangeStroke

# 同一塘口两个冲程开始时刻的最小间隔
STROKE_START_GAP = timedelta(minutes=30)


def get_active_stroke(db: Session, pond_id: int) -> WaterChangeStroke | None:
    """返回该塘口进行中（结束时刻为空）的冲程，没有则 None。"""
    return (
        db.query(WaterChangeStroke)
        .filter(
            WaterChangeStroke.pond_id == pond_id,
            WaterChangeStroke.end_at.is_(None),
        )
        .order_by(WaterChangeStroke.start_at.desc())
        .first()
    )


def changing_pond_ids(db: Session, pond_ids: list[int]) -> set[int]:
    """给定塘口集合，返回其中正在换水的塘口 id。"""
    if not pond_ids:
        return set()
    rows = (
        db.query(WaterChangeStroke.pond_id)
        .filter(
            WaterChangeStroke.pond_id.in_(pond_ids),
            WaterChangeStroke.end_at.is_(None),
        )
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def assert_pond_not_changing(db: Session, pond_id: int) -> None:
    """投喂互斥：该塘有进行中冲程时拒绝新建投喂（409）。"""
    active = get_active_stroke(db, pond_id)
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail=f"塘口正在进行换水冲程 #{active.id}，换水期间禁止投喂，冲程结束后恢复",
        )


def find_start_conflict(
    db: Session, pond_id: int, start_at: datetime
) -> WaterChangeStroke | None:
    """同塘口开始时刻前后半小时窗口内已有的冲程（含已结束的）。"""
    return (
        db.query(WaterChangeStroke)
        .filter(
            WaterChangeStroke.pond_id == pond_id,
            WaterChangeStroke.start_at >= start_at - STROKE_START_GAP,
            WaterChangeStroke.start_at <= start_at + STROKE_START_GAP,
        )
        .order_by(WaterChangeStroke.start_at)
        .first()
    )
