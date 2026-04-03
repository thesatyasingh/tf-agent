# Use an official lightweight Python image
FROM python:3.13-slim

# Install system dependencies (Git, curl, unzip) required for the agent tools
RUN apt-get update && apt-get install -y git curl unzip && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip -o terraform.zip \
    && unzip terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform.zip

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# --- THE HARDCODED CREDENTIALS ---
# Copy the local credentials file into the container
COPY lumen_creds.json /app/lumen_creds.json
# Tell GCP/Terraform to use this file for authentication
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/lumen_creds.json

# Cloud Run injects the PORT environment variable (default 8080)
ENV PORT=8000
EXPOSE $PORT

# --- START COMMAND ---
# Replace "main.py" with whatever file you normally run to start the agent locally.
CMD adk run main.py --host 0.0.0.0 --port $PORT