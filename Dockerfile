FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
RUN pip install -e .

CMD ["tail", "-f", "/dev/null"]
