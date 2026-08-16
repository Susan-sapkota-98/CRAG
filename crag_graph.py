import os
from typing import List, TypedDict
import re
from PIL import Image
from ocr_router import run_ocr
import time

from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel


# -----------------------------
# 1. Embeddings + LLM
# -----------------------------
embeddings = OllamaEmbeddings(model="nomic-embed-text")

UPPER_TH = 0.6
LOWER_TH = 0.2

INDEX_PATH = "faiss_index"


# ===== NAYA — multi-provider model support =====
_model_cache = {}

def get_model(provider: str, model_name: str, api_key: str = None):
    """
    provider: 'ollama' | 'huggingface' | 'openai'
    """
    cache_key = f"{provider}:{model_name}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    if provider == "ollama":
        m = ChatOllama(model=model_name, temperature=0, num_predict=300, keep_alive="30m")

    elif provider == "huggingface":
        from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
        endpoint = HuggingFaceEndpoint(
            repo_id=model_name,
            huggingfacehub_api_token=api_key,
            temperature=0.1,
            max_new_tokens=300,
        )
        m = ChatHuggingFace(llm=endpoint)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        m = ChatOpenAI(model=model_name, api_key=api_key, temperature=0)

    else:
        raise ValueError(f"Unknown provider: {provider}")

    _model_cache[cache_key] = m
    return m


# Default model at startup — same as before (Ollama qwen2.5:7b)
model = get_model("ollama", "qwen2.5:7b")
# ===== NAYA END =====


# -----------------------------
# 2. Vector store holder (mutable, so upload can replace/add)
# -----------------------------
_store = {"vector_store": None}


def _load_pdf_chunks(pdf_path: str) -> List[Document]:
    docs = PyPDFLoader(pdf_path).load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150).split_documents(docs)
    for d in chunks:
        d.page_content = d.page_content.encode("utf-8", "ignore").decode("utf-8", "ignore")
    return chunks


def init_index():
    """Load existing saved index if present, else leave empty."""
    if os.path.exists(INDEX_PATH):
        _store["vector_store"] = FAISS.load_local(
            INDEX_PATH, embeddings, allow_dangerous_deserialization=True
        )
    else:
        _store["vector_store"] = None


def _add_chunks_in_batches(chunks: List[Document], batch_size: int = 32, max_retries: int = 3):
    """
    Feeds chunks to Ollama for embedding in small batches instead of one
    giant request, so Ollama doesn't OOM/crash on large PDFs. Retries a
    batch a few times before giving up, in case Ollama is briefly busy.
    """

    if not chunks:
        return

    def add_with_retry(batch, is_first):
        for attempt in range(max_retries):
            try:
                if is_first and _store["vector_store"] is None:
                    _store["vector_store"] = FAISS.from_documents(batch, embeddings)
                else:
                    _store["vector_store"].add_documents(batch)
                return
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 * (attempt + 1))

    first_batch = chunks[:batch_size]
    remaining = chunks[batch_size:]

    add_with_retry(first_batch, is_first=True)

    for i in range(0, len(remaining), batch_size):
        add_with_retry(remaining[i:i + batch_size], is_first=False)


def add_pdf_to_index(pdf_path: str, mode: str = "add"):
    """
    mode = "replace" -> naya PDF le purano index replace garcha
    mode = "add"      -> naya PDF purano index ma accumulate huncha
    """
    chunks = _load_pdf_chunks(pdf_path)

    if mode == "replace":
        _store["vector_store"] = None

    _add_chunks_in_batches(chunks, batch_size=32)

    _store["vector_store"].save_local(INDEX_PATH)

def add_image_to_index(image_path: str, engine: str, mode: str = "add"):
    """
    engine: 'nepali_printed' | 'english_printed' | 'english_handwritten'
    """
    image = Image.open(image_path).convert("RGB")
    text = run_ocr(image, engine)

    doc = Document(
        page_content=text,
        metadata={"source": image_path.split("/")[-1], "page": 1, "ocr_engine": engine}
    )
    chunks = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150).split_documents([doc])

    # if mode == "replace" or _store["vector_store"] is None:
    #     _store["vector_store"] = FAISS.from_documents(chunks, embeddings)
    # else:
    #     _store["vector_store"].add_documents(chunks)

    # _store["vector_store"].save_local(INDEX_PATH)
    
    
    if mode == "replace":
        _store["vector_store"] = None

    _add_chunks_in_batches(chunks, batch_size=32)

    _store["vector_store"].save_local(INDEX_PATH)


def get_retriever():
    if _store["vector_store"] is None:
        return None
    return _store["vector_store"].as_retriever(search_kwargs={"k": 8})


init_index()


# -----------------------------
# 3. State
# -----------------------------
class State(TypedDict):
    question: str
    docs: List[Document]

    good_docs: List[Document]
    verdict: str
    reason: str

    strips: List[str]
    kept_strips: List[str]
    refined_context: str

    web_docs: List[Document]

    answer: str
    sources: List[str]


# -----------------------------
# 4. Retrieve node
# -----------------------------
def retrieve_node(state: State) -> State:
    retriever = get_retriever()
    if retriever is None:
        return {"docs": []}
    q = state["question"]
    return {"docs": retriever.invoke(q)}


# -----------------------------
# 5. Score-based doc evaluator
# -----------------------------
class DocEvalScore(BaseModel):
    score: float
    reason: str


doc_eval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a retrieval evaluator for RAG.\n"
            "You will be given ONE retrieved chunk and a question.\n"
            "Return a relevance score in [0.0, 1.0] based on how well the chunk "
            "helps answer the question, even partially.\n"
            "- 1.0: chunk directly defines, explains, or solves what the question asks\n"
            "- 0.7-0.9: chunk contains a clear definition, explanation, or example relevant to the question\n"
            "- 0.4-0.6: chunk is topically related but incomplete on its own\n"
            "- 0.0-0.2: chunk is unrelated to the question\n"
            "Note: chunks may contain garbled math notation, symbols, or broken formatting "
            "extracted from a PDF (e.g. equations, diagrams described as numbers). "
            "Do NOT penalize a chunk just because the math/notation looks messy — "
            "judge relevance based on the surrounding text, terms, and definitions present.\n"
            "Also return a short reason.\n"
            "Output JSON only.",
        ),
        ("human", "Question: {question}\n\nChunk:\n{chunk}"),
    ]
)

doc_eval_chain = doc_eval_prompt | model.with_structured_output(DocEvalScore)


def eval_each_doc_node(state: State) -> State:
    q = state["question"]
    docs = state["docs"]

    inputs = [{"question": q, "chunk": d.page_content} for d in docs]
    
    # Process in smaller batches to avoid GPU OOM
    batch_size = 2  # Adjust if needed (1-3 recommended for most GPUs)
    outs = []
    for i in range(0, len(inputs), batch_size):
        batch = inputs[i:i+batch_size]
        outs.extend(doc_eval_chain.batch(batch))

    scores: List[float] = [o.score for o in outs]
    good: List[Document] = [d for d, s in zip(docs, scores) if s > LOWER_TH]

    if good:
        return {
            "good_docs": good,
            "verdict": "CORRECT",
            "reason": f"Found {len(good)} relevant chunk(s) scoring above {LOWER_TH}.",
        }

    return {
        "good_docs": [],
        "verdict": "INCORRECT",
        "reason": f"All retrieved chunks scored below {LOWER_TH}.",
    }


# -----------------------------
# 6. Decompose -> Filter -> Recompose (refine)
# -----------------------------
def decompose_to_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


class KeepOrDrop(BaseModel):
    keep: bool


filter_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict relevance filter.\n"
            "Return keep=true only if the sentence directly helps answer the question.\n"
            "Use ONLY the sentence. Output JSON only.",
        ),
        ("human", "Question: {question}\n\nSentence:\n{sentence}"),
    ]
)

filter_chain = filter_prompt | model.with_structured_output(KeepOrDrop)


# ===== NAYA — call this from app.py when user switches model =====
def set_active_model(provider: str, model_name: str, api_key: str = None):
    global model, doc_eval_chain, filter_chain
    model = get_model(provider, model_name, api_key)
    doc_eval_chain = doc_eval_prompt | model.with_structured_output(DocEvalScore)
    filter_chain = filter_prompt | model.with_structured_output(KeepOrDrop)
# ===== NAYA END =====


def refine(state: State) -> State:
    q = state["question"]

    if state.get("verdict") == "CORRECT":
        context = "\n\n".join(d.page_content for d in state["good_docs"]).strip()
    else:
        context = "\n\n".join(d.page_content for d in state["web_docs"]).strip()

    strips = decompose_to_sentences(context)

    if strips:
        inputs = [{"question": q, "sentence": s} for s in strips]
        results = filter_chain.batch(inputs)  # parallel instead of one-by-one
        kept: List[str] = [s for s, r in zip(strips, results) if r.keep]
    else:
        
        kept = []

    refined_context = "\n".join(kept).strip()

    return {
        "strips": strips,
        "kept_strips": kept,
        "refined_context": refined_context,
    }


# -----------------------------
# 7. Web search node (DuckDuckGo)
# -----------------------------
ddg = DuckDuckGoSearchResults(output_format="list", num_results=5)


def web_search_node(state: State) -> State:
    q = state["question"]
    results = ddg.invoke(q)

    web_docs = []
    for r in results or []:
        title = r.get("title", "")
        url = r.get("link", "")
        content = r.get("snippet", "")
        text = f"TITLE: {title}\nURL: {url}\nCONTENT:\n{content}"
        web_docs.append(Document(page_content=text, metadata={"url": url, "title": title}))

    return {"web_docs": web_docs}

# -----------------------------
# 8. Generate node
# -----------------------------
answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful ML tutor. Answer ONLY using the provided context.\n"
            "If the context is empty or insufficient, say: 'I don't know.'",
        ),
        ("human", "Question: {question}\n\nRefined context:\n{refined_context}"),
    ]
)


def generate(state: State) -> State:
    out = (answer_prompt | model).invoke(
        {"question": state["question"], "refined_context": state["refined_context"]}
    )

    source_docs = state.get("good_docs") or state.get("web_docs") or []
    refs = []
    for d in source_docs:
        if "url" in d.metadata:
            refs.append(f"{d.metadata.get('title', 'Web result')} ({d.metadata['url']})")
        else:
            src = d.metadata.get("source", "unknown")
            page = d.metadata.get("page", "N/A")
            refs.append(f"{src} (pg.{page})" if page != "N/A" else src)
    refs = list(dict.fromkeys(refs))

    return {"answer": out.content, "sources": refs}

# -----------------------------
# 9. Ambiguous node + routing
# -----------------------------
def ambiguous_node(state: State) -> State:
    return {"answer": "I couldn't find a clear answer to this in your uploaded documents. Try rephrasing, or upload a document that covers this topic."}


def route_after_eval(state: State) -> str:
    if state["verdict"] == "CORRECT":
        return "refine"
    elif state["verdict"] == "INCORRECT":
        return "web_search"
    else:
        return "ambiguous"


# -----------------------------
# 10. Build graph
# -----------------------------
g = StateGraph(State)

g.add_node("retrieve", retrieve_node)
g.add_node("eval_each_doc", eval_each_doc_node)
g.add_node("web_search", web_search_node)
g.add_node("refine", refine)
g.add_node("generate", generate)
g.add_node("ambiguous", ambiguous_node)

g.add_edge(START, "retrieve")
g.add_edge("retrieve", "eval_each_doc")

g.add_conditional_edges(
    "eval_each_doc",
    route_after_eval,
    {
        "refine": "refine",
        "web_search": "web_search",
        "ambiguous": "ambiguous",
    },
)

g.add_edge("web_search", "refine")
g.add_edge("refine", "generate")

g.add_edge("generate", END)
g.add_edge("ambiguous", END)

app = g.compile()