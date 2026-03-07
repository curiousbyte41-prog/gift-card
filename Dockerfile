FROM python:3.11-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install dependencies - FIXED: removed problematic pip upgrade
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code and QR code
COPY bot.py .
COPY qr.jpg .

# Run bot
CMD ["python", "bot.py"]
