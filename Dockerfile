FROM python:3.10-slim

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your function code
COPY src src

CMD ["python", "-m", "src.signal_generation_engine"]
