# Base image with Python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy local code into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for Flask
ENV FLASK_APP=run.py

# Expose port
EXPOSE 5050

# Make startup script executable and run it
RUN chmod +x startup.sh
CMD ["./startup.sh"]
