# Use Python 3.12 slim
FROM python:3.12-slim

# Set working directory
WORKDIR /code

# Install system dependencies required for PDF processing (Camelot/Poppler)
RUN apt-get update && \
    apt-get install -y poppler-utils build-essential libgl1-mesa-glx ghostscript && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
# Based on your screenshot, you have a combined file
COPY combined_requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r combined_requirements.txt

# Copy the entire project into the container
COPY . .

# (CMD is handled by docker-compose)