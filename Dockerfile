FROM public.ecr.aws/lambda/python:3.10

WORKDIR /var/task

# Copy requirements and install dependencies
COPY requirements.txt .
# RUN pip install --upgrade pip \
#     && pip install -r requirements.txt -t .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy your function code
COPY src/ src/

CMD ["src.signals.signal_generation_engine.lambda_handler"]
