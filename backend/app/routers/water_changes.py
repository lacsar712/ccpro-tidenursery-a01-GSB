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
from app.services.water_change import ensure_aware, find_start_conflict, get_active_stroke

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
    return q.order_by(WaterChangeStroke.started_at.desc()).all()


@router.post("", response_model=WaterChangeStrokeOut, status_code=status.HTTP_201_CREATED)
def create_stroke(
    payload: WaterChangeStrokeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")

    # 干塘禁止开冲程
    if pond.status == "dry":
        raise HTTPException(status_code=409, detail="干塘禁止开换水冲程")

    # 隔离塘允许，但备注类说明必填
    if pond.status == "quarantine" and not (payload.notes and payload.notes.strip()):
        raise HTTPException(status_code=400, detail="隔离塘开换水冲程必须填写备注类说明")

    # 同一塘口同时只允许一条进行中冲程
    active = get_active_stroke(db, payload.pond_id)
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail=f"该塘已有进行中的换水冲程（编号 #{active.id}），需先结束",
        )

    # 开始时刻前后半小时内只允许一条冲程，冲突回显已有冲程编号
    conflict = find_start_conflict(db, payload.pond_id, payload.started_at)
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=f"开始时刻前后半小时内已存在冲程编号 #{conflict.id}，时间冲突",
        )

    item = WaterChangeStroke(
        pond_id=payload.pond_id,
        out_volume_m3=payload.out_volume_m3,
        in_volume_m3=payload.in_volume_m3,
        started_at=payload.started_at,
        ended_at=None,
        operator_name=payload.operator_name,
        notes=payload.notes,
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
    item = db.query(WaterChangeStroke).filter(WaterChangeStroke.id == stroke_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="换水冲程不存在")
    if item.ended_at is not None:
        raise HTTPException(status_code=409, detail=f"冲程编号 #{item.id} 已结束")
    if payload.ended_at <= ensure_aware(item.started_at):
        raise HTTPException(status_code=400, detail="结束时刻必须晚于开始时刻")

    item.ended_at = payload.ended_at

    # 同事务追加一条水质样：采样时刻=结束时刻，盐度取换入水约定默认值。
    # 只结束冲程、不写水质样不算完成，故与冲程更新同一事务提交。
    sample = WaterSample(
        pond_id=item.pond_id,
        sampled_at=payload.ended_at,
        temp_c=None,
        salinity_ppt=settings.incoming_water_salinity_ppt,
        do_mg_l=None,
        ph=None,
        notes=(
            f"换水冲程 #{item.id} 结束自动采样：盐度取换入水约定默认值 "
            f"{settings.incoming_water_salinity_ppt} ppt，水温/溶解氧/pH 待测"
        ),
    )
    db.add(sample)
    db.commit()
    db.refresh(item)
    return item
