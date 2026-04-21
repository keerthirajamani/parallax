FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src/ src/

CMD ["python", "-m", "src.signals.signal_generation_engine"]
