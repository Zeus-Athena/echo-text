FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set timezone to Asia/Shanghai (UTC+8)
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ONNX model is included in models/ directory (no runtime download needed)

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Make entrypoint script executable
RUN chmod +x /app/scripts/prestart.sh

# Set entrypoint
ENTRYPOINT ["/app/scripts/prestart.sh"]

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
