FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pandas
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy bot code and QR code
COPY bot.py .
COPY qr.jpg .

# Run bot
CMD ["python", "bot.py"]
