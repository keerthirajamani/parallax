FROM public.ecr.aws/lambda/python:3.10

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your function code
COPY signal_generation_engine.py .
COPY utils/ utils/

# Lambda handler
CMD ["signal_generation_engine.lambda_handler"]
