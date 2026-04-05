# TechTrend Python

A complete Python implementation of the Crucix Intelligence Engine.

## Quick Start

```bash
cd py
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env

python main.py
```

Dashboard: http://localhost:3117

## Features

- **29 Data Sources**: Complete OSINT coverage
- **Real-time Updates**: SSE-based live dashboard
- **Delta Detection**: Automatic change detection
- **LLM Trade Ideas**: Anthropic/OpenAI/Gemini support
- **Alert System**: Telegram + Discord notifications

## Data Sources

### Tier 1: Core OSINT & Geopolitical (11)
| Source | Description | Auth |
|--------|-------------|------|
| GDELT | Global news events | None |
| OpenSky | Flight tracking | None |
| NASA FIRMS | Fire detection | Free key |
| Maritime | Vessel tracking | Optional |
| Safecast | Radiation monitoring | None |
| ACLD | Conflict events | Free |
| ReliefWeb | Humanitarian crises | Optional |
| WHO | Disease outbreaks | None |
| OFAC | Sanctions | None |
| OpenSanctions | Global sanctions | None |
| ADS-B | Military flights | Optional |

### Tier 2: Economic & Financial (7)
| Source | Description | Auth |
|--------|-------------|------|
| FRED | Fed data | Free key |
| Treasury | Debt & yields | None |
| BLS | Employment | Optional |
| EIA | Energy | Free key |
| GSCPI | Supply chain | None |
| USAspending | Contracts | None |
| Comtrade | Trade flows | Optional |

### Tier 3: Weather, Tech, Social (7)
| Source | Description | Auth |
|--------|-------------|------|
| NOAA | Weather alerts | None |
| EPA | Radiation | None |
| Patents | Tech patents | None |
| Bluesky | Social | None |
| Reddit | Social | Optional |
| Telegram | OSINT channels | Optional |
| KiwiSDR | HF radio | None |

### Tier 4-6
| Source | Description |
|--------|-------------|
| CelesTrak | Satellite tracking |
| Yahoo Finance | Live market data |
| CISA KEV | Vulnerability catalog |
| Cloudflare Radar | Internet outages |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/data` | GET | Current intelligence data |
| `/api/health` | GET | System health |
| `/api/delta` | GET | Change detection results |
| `/api/sweep` | POST | Trigger manual sweep |
| `/api/events` | GET | SSE stream |

## Architecture

```
crucix/
├── __init__.py
├── config.py           # Configuration
├── engine.py          # Main orchestrator
├── delta.py           # Change detection
├── server.py          # FastAPI server
├── sources/           # 29 data sources
│   ├── tier1/        # OSINT sources
│   ├── tier2/        # Economic sources
│   ├── tier3/        # Social/Tech sources
│   ├── tier4/        # Space
│   ├── tier5/        # Market data
│   └── tier6/        # Cyber
├── llm/              # LLM providers
│   ├── anthropic.py
│   ├── openai.py
│   ├── gemini.py
│   └── ideas.py
├── alerts/           # Alert systems
│   ├── telegram.py
│   └── discord.py
└── dashboard/
    └── index.html
```

## License

AGPL-3.0
