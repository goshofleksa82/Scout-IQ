FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 scoutiq
COPY app ./app
COPY migrations ./migrations
COPY ops ./ops
COPY demo ./demo
COPY alembic.ini models.py create_admin.py database.py schemas.py security.py ./
USER 10001
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=7s --start-period=20s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8001')+'/health/ready',timeout=5)"
CMD ["python","ops/serve.py"]
