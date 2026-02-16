# Commander

## Documents

- [多子项目研发协同管理系统设计方案](docs/rd-collaboration-management-system-design.md)

## MVP 开发完成范围

已实现可运行后端（FastAPI + SQLite），覆盖：

- 项目群 / 子项目管理
- 流程模板管理
- 转测卡点规则与自动校验
- 评审记录与发布单校验
- 质量快照采集
- 项目群级风险看板
- 数据源事件接入接口

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问地址：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`

## 初始化演示数据

```bash
python -m app.seed_demo
```

## 运行测试

```bash
pytest -q
```

## 关键 API

- `POST /api/v1/programs`
- `POST /api/v1/workflow-templates`
- `POST /api/v1/subprojects`
- `POST /api/v1/subprojects/{id}/gate-rules`
- `POST /api/v1/subprojects/{id}/gate-checks`
- `POST /api/v1/subprojects/{id}/reviews`
- `POST /api/v1/subprojects/{id}/release-tickets`
- `POST /api/v1/subprojects/{id}/quality-snapshots`
- `GET /api/v1/dashboard/programs/{program_id}`
- `POST /api/v1/integrations/events`