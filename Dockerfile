# --- Stage 1: Build the React Frontend ---
# Use a Node.js base image to build our static assets
FROM node:18-alpine AS builder

# Set the working directory for the frontend build
WORKDIR /app/frontend

# Copy package files and install dependencies first to leverage Docker's layer caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ ./
COPY data/settings_default.json ./data/settings.json
#COPY .env /app/frontend
# Build the production-ready static files. The output will be in the /app/frontend/dist folder.
RUN npm run build

# --- Stage 2: Create the Final Python Application Image ---
# Use a slim Python base image for a smaller final size
FROM python:3.10-slim


RUN apt-get update && apt-get install -y \
    cifs-utils \
    util-linux \
    keyutils \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
#COPY cifs-mount.py .




# Set the working directory for the backend application
WORKDIR /app/backend

# Set environment variables for Python to run efficiently in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements file and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend application code into the container
COPY backend/ ./
COPY backend/cifs-mount.py ./
# --- The Magic Step: Copy the built frontend from the 'builder' stage ---
# This copies the static HTML, JS, and CSS files into a 'dist' folder inside our backend directory.
# The Node.js environment from Stage 1 is completely discarded.
COPY --from=builder /app/frontend/dist /app/backend/dist

# Expose the port the Flask application will run on
EXPOSE 5001

# The command to run the production-ready Gunicorn web server
# It will serve our Flask app, which in turn serves the static frontend files.
# Create entrypoint script that mounts shares then runs the main application
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting CIFS mounter..."\n\
python3 cifs-mount.py\n\
\n\
if [ $? -eq 0 ]; then\n\
    echo "CIFS shares mounted successfully"\n\
    echo "Mount status:"\n\
    python3 cifs-mount.py .env status\n\
else\n\
    echo "Failed to mount CIFS shares"\n\
    exit 1\n\
fi\n\
\n\
# If additional arguments provided, run them\n\
if [ $# -gt 0 ]; then\n\
    echo "Running additional command: $@"\n\
    exec "$@"\n\
else\n\
    echo "CIFS shares mounted. Container will keep running..."\n\
    # Keep container running\n\
    tail -f /dev/null\n\
fi' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

#CMD [ "gunicorn", "--bind", "0.0.0.0:5001", "app:app"]
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "1200", "--workers", "1", "--threads", "4", "app:app"]