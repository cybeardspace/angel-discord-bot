# Use the official Python 3.11 slim image as the base
FROM python:3.11-slim

# Set environment variables for better Python/Docker behavior
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /usr/src/app

# Create a virtual environment and install dependencies into it
RUN python -m venv venv

# Activate venv and upgrade pip, install requirements
# The whole RUN command is executed in a single shell session to respect venv activation
COPY requirements.txt .
RUN . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy the start script and give it execution permissions
COPY start-angel-bot.sh .
RUN chmod +x start-angel-bot.sh

# Copy the main application code (angel.py and any other files)
COPY . .

# Set the start script as the command to run when the container launches
CMD ["./start-angel-bot.sh"]