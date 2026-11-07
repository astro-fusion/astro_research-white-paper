# 🖥️ application/ — Web Interface & REST API

The `application/` directory contains the **user-facing components**: a Flask web application for interactive research exploration and a REST API for programmatic access.

---

## 📁 Structure

```
application/
├── web/                  ← Flask web application
│   ├── app.py            ← Main application module (routes, logic)
│   ├── web.py            ← WSGI entry point / server startup
│   ├── templates/        ← Jinja2 HTML templates
│   └── static/           ← CSS, JS, image assets
│
├── api/                  ← REST API
│   ├── api.py            ← API endpoint definitions (Flask/FastAPI)
│   └── api-client.js     ← JavaScript client library for the API
│
└── config/               ← Application configuration files
```

---

## 🚀 Running Locally

### Web Application

```bash
# Activate your virtual environment
source .venv/bin/activate

# Start the development server
python application/web/web.py

# → Open http://localhost:5000
```

### REST API

```bash
# Start the API server
python application/api/api.py

# → API available at http://localhost:8000
```

---

## 🌐 API Endpoints

| Method | Endpoint          | Description                             |
| ------ | ----------------- | --------------------------------------- |
| `GET`  | `/api/chart`      | Calculate a Vedic birth chart           |
| `GET`  | `/api/numerology` | Get numerology profile for a birth date |
| `GET`  | `/api/dignity`    | Get planetary dignity scores            |
| `GET`  | `/api/dasha`      | Get Vimshottari Dasha periods           |
| `GET`  | `/health`         | Health check                            |

### Example Request

```bash
curl "http://localhost:8000/api/numerology?birth_date=1984-08-27"
```

```json
{
  "mulanka": 9,
  "bhagyanka": 3,
  "planet": "Mars",
  "lo_shu_grid": [...]
}
```

---

## 🛠️ Configuration

Runtime configuration is loaded from environment variables (or a `.env` file):

```bash
# Create .env from the example
cp ops/config/.env.example .env
# → Edit .env with your settings
```

| Variable         | Default      | Description                  |
| ---------------- | ------------ | ---------------------------- |
| `PORT`           | `5000`       | Web server port              |
| `API_PORT`       | `8000`       | API server port              |
| `EPHEMERIS_PATH` | `libs/ephe/` | Path to Swiss Ephemeris data |
| `DEBUG`          | `false`      | Enable debug mode            |

---

## 🏗️ Architecture Notes

- The web app and API are **stateless** — all data is computed on-demand from the `libs/` library
- No database required for basic operation
- The JS client (`api-client.js`) can be used standalone in browser environments

---

## 🤝 Contributing to the Application

- Follow the Flask patterns already established in `app.py`
- Add tests for new routes in `tests/test_e2e_complete.py` or `tests/test_e2e_playwright.py`
- Never commit API keys or secrets — use environment variables only
