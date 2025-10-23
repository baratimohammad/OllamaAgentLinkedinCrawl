FROM python:3.12-slim

# Set working dir
WORKDIR /app

# Copy code
COPY app/ /app/
COPY shared_data/ /shared_data/
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt



# Set default command
# ENTRYPOINT ["python", "EmploymentAgent.py"]
ENTRYPOINT ["python", "-u", "SummarizeAgent.py"]

ENV PYTHONUNBUFFERED=1
