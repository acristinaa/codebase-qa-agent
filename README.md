# codebase-qa-agent

A Q&A agent that answers questions about a real codebase, what a function does,
what calls it, and what would break if it changed. It combines semantic search
(RAG) over the code with discrete tools (file reading, dependency lookup), and
chains multiple tool calls to reason through a question rather than doing a single
retrieve-and-answer pass.

## How it works

1. **Ingest** — `ingest.py` walks the target repo and uses Python's `ast` module
   to extract every function, class, and method as a chunk (name, source, file,
   line range, docstring, imports), saved to `chunks.json`.
2. **Retrieval** — `embed.py` embeds each chunk with OpenAI `text-embedding-3-small`
   and stores the vectors in a local Chroma database. `search.py` embeds a query
   and returns the closest chunks.
3. **Tools** — `tools.py` exposes four functions the agent can call:
   `search_code` (semantic search), `read_file` (read a line range),
   `find_dependents` (grep for callers), and `find_definition` (find where a
   name is defined).
4. **Agent** — `agent.py` runs a tool-use loop with OpenAI function calling. The
   model decides which tools to call, chains them, and answers grounded in what
   the tools returned.
5. **Interface** — `cli.py` is an interactive prompt for asking questions.

## Setup

Requires Python 3.8+ and an API key from an LLM provider

```bash
# 1.Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate 

# 2. Install dependencies
pip install -r requirements.txt

# 3.Add your OpenAI key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "OPENAI_MODEL=gpt-4o" >> .env

# 4. Clone a repo to analyze into target_repo/ (gitignored)
git clone --depth 1 https://github.com/pallets/flask.git target_repo
```

## Usage

Run the pipeline once to build the index:

```bash
python ingest.py     # parse target_repo/ -> chunks.json
python embed.py      # embed chunks -> chroma_db/
```

Then ask questions:

```bash
python cli.py
```