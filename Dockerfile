FROM python:3.12-slim

# Set working dir
WORKDIR /app

# Copy code
COPY app /app

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
    pandas \
    tavily-python \
    langchain \
    langchain_ollama \
    langgraph \
    instructor \
    pydantic \
    openpyxl \
    httpx \
    requests

# Set default command
CMD ["python", "transform.py"]
