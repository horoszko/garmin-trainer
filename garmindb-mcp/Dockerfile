FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "mcp[cli]"

COPY app.py .
COPY config.py .
COPY sport_categories.py .

CMD ["python", "app.py"]
