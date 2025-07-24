# LLM Document Browser

Author: Michael Koscheck
Last revised: Jul 21 2025

## Context

This tool is viewed as the deliverable for the course *Artificial Intelligence in Business* that takes place at the *Kozminski University* as part of their International Summer School 2025 program.

As I created this with the intention for other students to use this as functional example and inspiration I have also created a [ReadMe file for people who are complete beginners at programming](./beginners.md) as I think this task will be almost impossible to do in just a week for those people.

## Requirements

Python version: 3.12.11 (other versions might be compatible but no guarantee)


## Usage

Start by installing the requirements (preferably in a virtual environment) and ensure [Ollama](https://ollama.com/) is running with the `deepseek-r1` model:

```bash
pip install -r requirements.txt
ollama pull deepseek-r1
```

The application exposes a simple command line interface:

- `python app.py ingest --path ./docs` – index all files in the given folder. Use `--reset` to clear the database first.
- `python app.py ask "your question"` – ask a question. The engine uses a hybrid search (semantic + keyword) over the persistent database and can analyse CSV files via pandas when needed.
- `python app.py status` – display how many document chunks are stored.

By default the vector database is stored in `./chroma_db`. Set the environment variable `CHROMA_PATH` to change this location.

## Docker

The repository contains a `Dockerfile` and `docker-compose.yml` to run the application together with an Ollama server. Build the images and run commands via compose:

```bash
docker compose pull
docker compose build
# show available CLI commands
docker compose run --rm app --help
```

When using the container you can ingest documents or ask questions, e.g.:

```bash
docker compose run --rm app ingest --path ./docs
docker compose run --rm app ask "your question"
```

The `ollama` service requires GPU access for best performance. Make sure your Docker environment exposes the GPU to the containers (for example using `--gpus all`).

## Azure deployment with Terraform

The `infra` directory holds a minimal Terraform setup for a GPU-enabled virtual machine. Provide your SSH public key and apply:

```bash
cd infra
terraform init
terraform apply -var="ssh_public_key=$(cat ~/.ssh/id_rsa.pub)"
```

The VM installs Docker automatically via cloud-init. After the machine is ready, SSH into it using the public IP output by Terraform and run:

```bash
docker compose pull
docker compose up -d
```

This starts the Ollama service and prepares the CLI so you can ingest documents and ask questions remotely.

Port **8000** is opened in the VM firewall so the web UI is reachable once the
containers are running.

## Web UI

A simple FastAPI application exposes a web interface that resembles the ChatGPT layout. It lets you ask questions and upload new documents directly from your browser. After deploying the Docker setup on Azure, access the UI via:

```
http://<public-ip>:8000
```

Uploaded files are stored in the `uploads/` directory and immediately ingested into the vector store.
You can remove uploaded files again via the UI. The "Ask" button is disabled while an upload is in progress to ensure all documents are indexed before querying.
