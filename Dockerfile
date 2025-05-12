FROM nvidia/cuda:11.6.2-cudnn8-runtime-ubuntu20.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.8 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libsndfile1 \
    git \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python aliases
RUN ln -sf /usr/bin/python3.8 /usr/bin/python && \
    ln -sf /usr/bin/python3.8 /usr/bin/python3

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package in development mode
RUN pip3 install -e .

# Create directories for data
RUN mkdir -p /data/input /data/output /data/temp

# Set environment variables for the application
ENV AUDIO_ANALYSIS_INPUT_DIR=/data/input \
    AUDIO_ANALYSIS_OUTPUT_DIR=/data/output \
    AUDIO_ANALYSIS_TEMP_DIR=/data/temp

# Set the entrypoint
ENTRYPOINT ["python", "-m", "audio_analysis.main"]

# Default command (can be overridden)
CMD ["--input_dir", "/data/input", "--output_dir", "/data/output"]