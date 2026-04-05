# TechTrend

技术情报监控仪表板 - 追踪 HackerNews、GitHub、AI 项目、自动驾驶领域动态

## 快速开始

```bash
cd py
pip install -r requirements.txt
cp .env.example .env
# 配置 API keys

python main.py
```

访问 http://localhost:3117

## 功能特性

- **实时数据源**: HackerNews、GitHub Trending、AI 项目、专利数据
- **SSE 流式更新**: 前端实时接收数据推送
- **变化检测**: 自动识别新趋势和热门话题
- **LLM 智能分析**: 支持 OpenAI/Anthropic/Gemini
- **多渠道告警**: Telegram + Discord 通知

## 数据源

| 数据源 | 说明 |
|--------|------|
| HackerNews | 技术热点追踪 |
| GitHub Trending | 开源项目趋势 |
| AI Projects | AI/ML 项目动态 |
| Patents | 专利数据库 |

## 项目结构

```
techtrend/
├── config.py           # 配置管理
├── engine.py           # 核心引擎
├── delta.py            # 变化检测
├── server.py           # FastAPI 服务
├── sources/           # 数据源
│   ├── tech.py        # 科技数据源
│   ├── tier1-tier6/   # 其他数据源
├── llm/               # LLM 集成
├── alerts/            # 告警系统
└── techdashboard/     # 前端仪表板
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 仪表板页面 |
| `/api/data` | GET | 获取当前数据 |
| `/api/health` | GET | 健康检查 |
| `/api/delta` | GET | 变化检测结果 |
| `/api/events` | GET | SSE 事件流 |

## 技术栈

- **后端**: Python 3.12 + FastAPI
- **前端**: 原生 HTML/JS
- **部署**: Docker

## License

AGPL-3.0
