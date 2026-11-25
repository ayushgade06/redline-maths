# One container: FastAPI engine serving the built React app (same origin, no CORS).
FROM node:22-alpine AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/engine
COPY engine/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY engine/ ./
COPY --from=web /app/web/dist /app/web/dist
RUN useradd --create-home redline && python -c "import sympy, main"  # fail the build early on import errors
USER redline
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
