# Deployment

## Streamlit
Deploy the repository to a Streamlit-compatible host and use:
`streamlit run app/streamlit_app.py`

## FastAPI
Use:
`uvicorn service.api:app --host 0.0.0.0 --port 8000`

The API exposes:
- `GET /health`
- `GET /metrics`
- `POST /score`

Example request:
```json
{"sku_id":"SKU001"}
```

## Docker
Build:
`docker build -t foresight .`

The image runs the pipeline during build, producing deterministic model artifacts.
For a production multi-service deployment, use `docker compose up --build`.
