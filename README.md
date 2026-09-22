# TideNursery-01 · 潮汐育苗台账

海水育苗场「塘口水质采样与投喂事件」台账种子项目（非库存 / 电商 / 医院）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic v2 · python-jose · passlib(bcrypt) · uvicorn |
| 前端 | React 18 · Vite · TypeScript · React Router v6 |
| 数据库 | PostgreSQL 15 |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3400** |
| 后端 API | **8400** |
| PostgreSQL | **5434** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 场长 |
| `technician` | `123456` | 水质技术员 |

## 一键启动

```bash
cd TideNursery-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3400
- 后端健康检查：http://localhost:8400/api/health
- API 文档：http://localhost:8400/docs

后端 entrypoint 流程：等待数据库就绪 → `create_all` 建表 → seed 初始数据 → 启动 uvicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 Password），`/api/auth/login`、`/api/auth/me`
2. **Hatchery 育苗场**：`name`、`seawaterSource`、`notes`
3. **Pond 育苗塘**：`hatcheryId`、`pondCode`、`species`、`volumeM3`、`status(stocked|dry|quarantine)`；同场 `pondCode` 唯一
4. **WaterSample 水质样**：`pondId`、`sampledAt`、`tempC`、`salinityPpt`、`doMgL`、`ph`、`notes`；`doMgL > 0` 且 `ph ∈ [6,9]`，否则返回 **400**
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`
6. **WaterChangeStroke 换水冲程**：见下节
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg

## 换水冲程（换水台账）

字段：`pondId`（所属塘口）、`outVolumeM3`（换出立方数，必须 > 0）、`inVolumeM3`（换入立方数，必须 > 0）、`startedAt`（开始时刻）、`endedAt`（结束时刻，进行中为空）、`operatorName`（操作人）、`notes`（备注）。

规则：

- **挂塘口、与投喂互斥**：冲程结束时刻为空 = 进行中，此时该塘**禁止新建投喂**（`POST /api/feed-events` 返回 **409** 并回显进行中冲程编号）；结束后恢复。互斥判定与冲程状态共用 `app/services/water_change.py` 的同一组函数（`get_active_stroke` / `is_pond_water_changing` / `assert_feed_allowed`），不是只登记不拦截。
- **开始时刻半小时互斥**：同一塘口在新冲程 `startedAt` 前后 30 分钟内只允许一条冲程，冲突返回 **409** 并回显已有冲程编号（`POST /api/water-changes`）。
- **干塘 / 隔离塘**：`dry` 干塘禁止开冲程（**409**）；`quarantine` 隔离塘允许开，但 `notes` 必填，否则 **400**。
- **结束冲程**：`POST /api/water-changes/{id}/finish`，`endedAt` 必须晚于 `startedAt`（否则 **400**）。结束时**同一事务**追加一条 `WaterSample`：`sampledAt = endedAt`、盐度取换入水约定默认值 **30 ppt**（`INCOMING_WATER_SALINITY_PPT`，见后端配置），水温 / 溶解氧 / pH 留空待测；只更新冲程不写水质样不算完成（同一 commit，失败整体回滚）。
- 塘口列表与详情每个塘口返回 `waterChanging`（是否正在换水）；种子数据含一条进行中冲程（A-01）。

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · FeedEvents · WaterChanges（侧栏「换水冲程」；塘口列表每行显示是否正在换水）

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://tidenursery:tidenursery@localhost:5434/tidenursery
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8400

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
TideNursery-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── models/
│       ├── schemas/
│       └── routers/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
