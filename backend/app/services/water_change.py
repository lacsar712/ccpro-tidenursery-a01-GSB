"""换水冲程状态与互斥判定（投喂互斥与冲程状态共用本模块函数）。"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.water_change_stroke import WaterChangeStroke

# 同一塘口两条冲程开始时刻的最小间隔（前后半小时）
STROKE_START_GAP = timedelta(minutes=30)


def ensure_aware(dt: datetime) -> datetime:
    """库内时间可能为 naive（SQLite），按 UTC 补齐，保证可比较。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_active_stroke(db: Session, pond_id: int) -> Optional[WaterChangeStroke]:
    """该塘口正在进行中（结束时刻为空）的冲程，没有则 None。"""
    return (
        db.query(WaterChangeStroke)
        .filter(
            WaterChangeStroke.pond_id == pond_id,
            WaterChangeStroke.ended_at.is_(None),
        )
        .order_by(WaterChangeStroke.started_at.desc())
        .first()
    )


def is_pond_water_changing(db: Session, pond_id: int) -> bool:
    """冲程状态：是否正在换水。"""
    return get_active_stroke(db, pond_id) is not None


def active_stroke_pond_ids(db: Session, pond_ids: list[int]) -> set[int]:
    """批量判定一批塘口中哪些正在换水，供列表展示，避免 N+1。"""
    if not pond_ids:
        return set()
    rows = (
        db.query(WaterChangeStroke.pond_id)
        .filter(
            WaterChangeStroke.pond_id.in_(pond_ids),
            WaterChangeStroke.ended_at.is_(None),
        )
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def assert_feed_allowed(db: Session, pond_id: int) -> None:
    """投喂互斥判定：该塘有进行中冲程则 409，回显冲程编号。"""
    stroke = get_active_stroke(db, pond_id)
    if stroke is not None:
        raise HTTPException(
            status_code=409,
            detail=f"塘口正在换水（冲程编号 #{stroke.id} 进行中），禁止新建投喂，结束后恢复",
        )


def find_start_conflict(
    db: Session, pond_id: int, started_at: datetime
) -> Optional[WaterChangeStroke]:
    """同一塘口在开始时刻前后半小时内已有的冲程。"""
    started_at = ensure_aware(started_at)
    candidates = (
        db.query(WaterChangeStroke)
        .filter(WaterChangeStroke.pond_id == pond_id)
        .order_by(WaterChangeStroke.started_at)
        .all()
    )
    for stroke in candidates:
        if abs(ensure_aware(stroke.started_at) - started_at) <= STROKE_START_GAP:
            return stroke
    return None
