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
6. **WaterChangeStroke 换水冲程**：`pondId`、`outflowM3(换出)`、`inflowM3(换入)`、`startAt`、`endAt(可空)`、`operatorName`、`note`
   - 冲程挂塘口：`outflowM3` 与 `inflowM3` 都必须为正数（Pydantic `gt=0`，否则 400）。
   - **与投喂互斥**：冲程进行中（`endAt` 为空）时该塘禁止新建投喂，投喂接口返回 **409** 并回显进行中的冲程编号；冲程结束后自动恢复。互斥判定与冲程状态共用 `app/services/water_change.py` 中的函数（`get_active_stroke` / `assert_pond_not_changing`），不是只做登记表。
   - **半小时冲突**：同一塘口在 `startAt` 前后 30 分钟窗口内只允许一条冲程（含已结束的），冲突返回 **409** 并回显已有冲程编号与开始时刻。
   - **开冲程限制**：干塘（`dry`）禁止开冲程（400）；隔离塘（`quarantine`）允许，但备注类说明 `note` 必填（400）。
   - **结束冲程**：`POST /api/water-changes/{id}/finish`，必须写入 `endAt` 且晚于 `startAt`（否则 400）；**同事务**追加一条水质样——采样时刻等于结束时刻，盐度取换入水约定默认值，其余未测指标（水温 / 溶解氧 / pH）留空。只写结束时刻、不写水质样不算完成（异常整体回滚）。自动水质样 id 回写到冲程的 `closingSampleId`。
   - 塘口对象带只读字段 `waterChanging`，标识该塘是否有进行中冲程；塘口列表每行展示「正在换水」。
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg

## 换入水默认盐度约定

结束换水冲程自动追加水质样时，盐度（`salinityPpt`）统一取**换入水约定默认值 30 ppt**，由后端配置
`INLET_DEFAULT_SALINITY_PPT`（见 `backend/app/config.py`，默认 `30.0`）控制，可通过环境变量覆盖。
自动采样只记录盐度，水温 / 溶解氧 / pH 不臆造，留空（`null`）展示为 `—`；该水质样 `notes` 注明来源冲程编号。

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · FeedEvents · WaterChanges（侧栏「换水冲程」，可开冲程 / 结束冲程）

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
