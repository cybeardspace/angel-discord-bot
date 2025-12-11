````markdown
# Angel Discord Bot: Docker Deployment Guide

This guide provides instructions for building and running the Angel Discord Bot using Docker Compose.

## 1. Prerequisites

Ensure you have Docker Engine and Docker Compose installed and accessible from your command line.

## 2. Setup

### A. Required Files

Confirm that the following files are present in your deployment directory:

* `Dockerfile`
* `docker-compose.yaml`
* `start-angel-bot.sh`
* `angel.py` (and all other application files)
* `requirements.txt`

### B. Configure Bot Token

Open the `docker-compose.yaml` file and replace the placeholder with your actual Discord Bot Token:

```yaml
    environment:
      - DISCORD_BOT_TOKEN=YOUR_ACTUAL_DISCORD_TOKEN_HERE
````

### C. Data Persistence

The configuration file (`angel_config.json`) is persisted using a **Docker Named Volume** (`angel_bot_data`). This ensures that all bot settings are saved across container restarts without being stored directly in your local project folder.

## 3. Deployment

### A. Build and Run the Service

Execute the following command in the directory containing your `docker-compose.yaml`. This command will build the Docker image and start the container in detached mode (`-d`).

```bash
docker compose up -d
```

### B. Monitoring and Logs

To verify the container is running and check for any startup errors:

```bash
# Check container status
docker ps

# Stream the bot's logs
docker compose logs -f angel-bot-service
```

## 4. Maintenance

### A. Stop the Service

To stop the running container while keeping the persistent volume data intact:

```bash
docker compose stop
```

### B. Stop and Remove Everything (Cleanup)

To stop the container, remove the container, and **delete the persistent volume** (`angel_bot_data`) and all bot settings:

```bash
docker compose down -v
```

*Note: The `-v` flag is critical for deleting the persistent volume.*

````
