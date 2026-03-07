FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code and assets
COPY bot.py .
COPY qr.jpg .

# Create volume for database
VOLUME ["/app/data"]

# Run bot
CMD ["python", "bot.py"]
