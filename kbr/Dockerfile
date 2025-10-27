# Use official Python slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install any system dependencies if needed
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Streamlit configuration
RUN mkdir -p ~/.streamlit
RUN echo "\
[server]\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
headless = true\n\
maxUploadSize = 200\n\
port = 8080\n\
" > ~/.streamlit/config.toml

# Run Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
