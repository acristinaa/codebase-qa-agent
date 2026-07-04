import json
from pathlib import Path

import chromadb
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CHUNKS_FILE = "chunks.json"
CHROMA_DIR = "chroma_db"
COLLECTION = "code_chunks"
EMBED_MODEL = "text-embedding-3-small"
BATCH = 100
MAX_TOKENS = 8000  # stay under the model's 8192 limit with margin

client_oai = OpenAI()
_encoding = tiktoken.get_encoding("cl100k_base")


def truncate(text, max_tokens=MAX_TOKENS):
    """Cut text down to max_tokens, measured with OpenAI's own tokenizer."""
    tokens = _encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return _encoding.decode(tokens[:max_tokens])


def embed_texts(texts):
    out = []
    for i in range(0, len(texts), BATCH):
        resp = client_oai.embeddings.create(model=EMBED_MODEL, input=texts[i:i + BATCH])
        out.extend(d.embedding for d in resp.data)
    return out


def chunk_to_text(c):
    parts = [f"{c['type']} {c['qualname']} in {c['file']}"]
    if c.get("docstring"):
        parts.append(c["docstring"])
    if c.get("source"):
        parts.append(c["source"])
    return truncate("\n\n".join(parts))


def main():
    chunks = json.loads(Path(CHUNKS_FILE).read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks")

    seen, ids = {}, []
    for c in chunks:
        cid = c["id"]
        if cid in seen:
            seen[cid] += 1
            cid = f"{cid}#{seen[cid]}"
        else:
            seen[cid] = 0
        ids.append(cid)

    print("Embedding (one API call per 100 chunks)...")
    vectors = embed_texts([chunk_to_text(c) for c in chunks])

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=[c.get("source") or "" for c in chunks],
        metadatas=[{
            "file": c["file"],
            "name": c["name"],
            "qualname": c["qualname"],
            "type": c["type"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "docstring": c.get("docstring") or "",
        } for c in chunks],
    )
    print(f"Stored {collection.count()} chunks in ./{CHROMA_DIR} (collection '{COLLECTION}')")


if __name__ == "__main__":
    main()