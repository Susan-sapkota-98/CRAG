# test_retrieval.py
from crag_graph import app

res = app.invoke({
    "question": "What is Recursion tree method?",
    "docs": [], "good_docs": [], "verdict": "", "reason": "",
    "strips": [], "kept_strips": [], "refined_context": "",
    "web_docs": [], "answer": "",
})

for i, d in enumerate(res["docs"]):
    print(f"--- Chunk {i} ---")
    print(d.page_content[:500])
    print()