from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.pond import Pond
from app.models.user import User
from app.models.water_change_stroke import WaterChangeStroke
from app.models.water_sample import WaterSample
from app.schemas.water_change_stroke import (
    WaterChangeStrokeCreate,
    WaterChangeStrokeFinish,
    WaterChangeStrokeOut,
)
from app.services.water_change import (
    find_start_conflict,
    get_active_stroke,
)

router = APIRouter(prefix="/api/water-changes", tags=["water-changes"])


@router.get("", response_model=List[WaterChangeStrokeOut])
def list_strokes(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(WaterChangeStroke)
    if pond_id is not None:
        q = q.filter(WaterChangeStroke.pond_id == pond_id)
    return q.order_by(WaterChangeStroke.start_at.desc()).all()


@router.post("", response_model=WaterChangeStrokeOut, status_code=status.HTTP_201_CREATED)
def start_stroke(
    payload: WaterChangeStrokeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")

    # 干塘禁止开冲程；隔离塘允许，但备注类说明必填
    if pond.status == "dry":
        raise HTTPException(status_code=400, detail="干塘禁止开换水冲程")
    if pond.status == "quarantine" and not (payload.note and payload.note.strip()):
        raise HTTPException(
            status_code=400, detail="隔离塘开换水冲程必须填写备注类说明"
        )

    # 同一塘口同时只允许一条进行中冲程（也与投喂互斥共用该状态）
    active = get_active_stroke(db, payload.pond_id)
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail=f"该塘口已有进行中的换水冲程 #{active.id}，请先结束后再开新冲程",
        )

    # 开始时刻前后半小时内只允许一条冲程，冲突回显已有冲程编号
    conflict = find_start_conflict(db, payload.pond_id, payload.start_at)
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"开始时刻前后半小时内已存在换水冲程 #{conflict.id}"
                f"（开始于 {conflict.start_at:%Y-%m-%d %H:%M}），请勿重复开冲程"
            ),
        )

    item = WaterChangeStroke(
        pond_id=payload.pond_id,
        outflow_m3=payload.outflow_m3,
        inflow_m3=payload.inflow_m3,
        start_at=payload.start_at,
        end_at=None,
        operator_name=payload.operator_name,
        note=payload.note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{stroke_id}/finish", response_model=WaterChangeStrokeOut)
def finish_stroke(
    stroke_id: int,
    payload: WaterChangeStrokeFinish,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stroke = db.query(WaterChangeStroke).filter(WaterChangeStroke.id == stroke_id).first()
    if not stroke:
        raise HTTPException(status_code=404, detail="换水冲程不存在")
    if stroke.end_at is not None:
        raise HTTPException(status_code=400, detail="该冲程已结束")

    # 结束时刻必须晚于开始时刻
    if payload.end_at <= stroke.start_at:
        raise HTTPException(status_code=400, detail="结束时刻必须晚于开始时刻")

    salinity = settings.inlet_default_salinity_ppt

    # 同事务：写结束时刻 + 追加一条水质样。只结束冲程不写水质样不算完成。
    sample = WaterSample(
        pond_id=stroke.pond_id,
        sampled_at=payload.end_at,
        temp_c=None,
        salinity_ppt=salinity,
        do_mg_l=None,
        ph=None,
        notes=(
            f"换水冲程 #{stroke.id} 结束自动采样：换入水盐度按约定默认 {salinity:g} ppt"
        ),
    )
    db.add(sample)
    try:
        db.flush()  # 取到 sample.id；失败则整体回滚，冲程不会被结束
        stroke.end_at = payload.end_at
        stroke.closing_sample_id = sample.id
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="结束冲程失败，已回滚（未写结束时刻）")
    db.refresh(stroke)
    return stroke
