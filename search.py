import sys

import chromadb

from embed import embed_texts, CHROMA_DIR, COLLECTION


def search(query, k=5):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION)
    q_vec = embed_texts([query])[0]
    res = collection.query(query_embeddings=[q_vec], n_results=k)

    hits = []
    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i]
        hits.append({
            "qualname": meta["qualname"],
            "file": meta["file"],
            "lines": f"{meta['start_line']}-{meta['end_line']}",
            "distance": res["distances"][0][i],
        })
    return hits


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "how is a route registered"
    print(f"Query: {query}\n")
    for h in search(query, k=5):
        print(f"{h['distance']:.3f}  {h['qualname']}  ({h['file']}:{h['lines']})")