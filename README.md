# LLM Document Browser

Author: Michael Koscheck
Last revised: Jul 21 2025

## Context

This tool is viewed as the deliverable for the course *Artificial Intelligence in Business* that takes place at the *Kozminski University* as part of their International Summer School 2025 program.

As I created this with the intention for other students to use this as functional example and inspiration I have also created a [ReadMe file for people who are complete beginners at programming](./beginners.md) as I think this task will be almost impossible to do in just a week for those people.

## Requirements

Python version: 3.12.11 (other versions might be compatible but no guarantee)


## Usage

Start by installing the requirements (preferably in a virtual environment):

```bash
pip install -r requirements.txt
```

The application exposes a simple command line interface:

- `python app.py ingest --path ./docs` – index all files in the given folder. Use `--reset` to clear the database first.
- `python app.py ask "your question"` – ask a question. The engine uses a hybrid search (semantic + keyword) over the persistent database and can analyse CSV files via pandas when needed.
- `python app.py status` – display how many document chunks are stored.

By default the vector database is stored in `./chroma_db`. Set the environment variable `CHROMA_PATH` to change this location.
