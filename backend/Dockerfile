FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -u 1000 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/models && python -c "\
from app.services.detector import FaceDetector; \
d = FaceDetector(model_dir='/app/models'); \
d.download_yunet_model(); \
d.download_sface_model()"

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
