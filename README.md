# RAG Document Intelligence Engine

A production-grade **Retrieval-Augmented Generation (RAG) system** that combines intelligent query routing, HyDE retrieval, cross-encoder reranking, and real-time streaming generation. Built with FastAPI, Next.js, ChromaDB, and Groq LLaMA.

**Status:** Fully functional, Docker-ready, RAGAS-evaluated, portfolio-grade.

---

## 🎯 Overview

This system answers questions about uploaded PDF documents with **cited sources**. Every claim in the answer is tagged `[C1]`, `[C2]`, etc. and linked to the exact source chunk with page numbers.

**Key capability:** Automatically detects query complexity and routes to the optimal retrieval strategy:
- **Simple queries** → Direct embedding search (fast, ~400ms)
- **Complex queries** → HyDE + reranking (accurate, ~1300ms)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER QUESTION                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  QUERY ROUTER   │ (Groq LLaMA)
                    │ (Simple/Complex)│
                    └────┬────────┬───┘
           ┌────────────┘         └──────────────┐
           │                                      │
    SIMPLE PATH                            COMPLEX PATH
    (~400ms)                               (~1300ms)
           │                                      │
    ┌──────▼──────┐                    ┌─────────▼────────┐
    │   Embed     │                    │ HyDE Generator   │
    │  Question   │                    │ (Groq LLaMA)     │
    └──────┬──────┘                    └────────┬─────────┘
           │                                    │
    ┌──────▼──────────────┐           ┌────────▼─────────┐
    │ ChromaDB Vector     │           │ Embed Hypothetical
    │ Search (k=8)        │           │ Answer            │
    │ Cosine Similarity   │           └────────┬──────────┘
    └──────┬──────────────┘                    │
           │                      ┌─────────────▼──────────┐
           │                      │ ChromaDB Vector Search │
           │                      │ (k=24)                 │
           │                      └─────────────┬──────────┘
           │                                    │
           │                      ┌─────────────▼──────────┐
           │                      │ MS MARCO Reranker     │
           │                      │ (Top 5)                │
           │                      └─────────────┬──────────┘
           │                                    │
           └────────────────┬───────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │  Groq LLaMA 3.3    │
                  │  Generate Answer   │
                  │  with Citations    │
                  └────────┬───────────┘
                           │
                  ┌────────▼────────┐
                  │  Stream Tokens  │
                  │  to Frontend    │
                  │  (SSE)          │
                  └────────┬────────┘
                           │
              ┌────────────▼──────────────┐
              │  Browser UI Renders       │
              │  Answer with [C1] Badges  │
              │  + Source Panel           │
              └───────────────────────────┘
```

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **Query Routing** | Automatic classification of simple vs complex queries via LLM |
| **HyDE Retrieval** | Generates hypothetical answers to improve semantic search accuracy |
| **Cross-Encoder Reranking** | Local MS MARCO MiniLM reranker for precise relevance scoring |
| **Real-Time Streaming** | Token-by-token generation via Server-Sent Events (SSE) |
| **Citation System** | Every answer claim tagged [C1], [C2], etc with source attribution |
| **User API Keys** | Users bring their own OpenAI + Groq keys (sessionStorage, never on server) |
| **Vector Persistence** | ChromaDB stores embeddings with metadata (source, page, chunk_index) |
| **Docker Ready** | Multi-stage builds for lean ~500MB production images |
| **RAGAS Evaluated** | Benchmarked with faithfulness, relevancy, and recall metrics |
| **Type-Safe** | Full TypeScript frontend + Pydantic backend validation |

---

## 🛠️ Tech Stack

```
Frontend:      Next.js 16 | TypeScript | Tailwind CSS | React 18
Backend:       FastAPI | Python 3.11 | LangChain | Pydantic
Vector DB:     ChromaDB (local, persisted)
Embeddings:    OpenAI text-embedding-3-small
LLM:           Groq llama-3.3-70b-versatile (free)
Reranker:      sentence-transformers (MS MARCO MiniLM-L-6-v2)
Evaluation:    RAGAS (faithfulness, relevancy, recall)
Deployment:    Docker | Docker Compose | AWS EC2 + ECR (optional)
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker** (optional, for containerized setup)
- **API Keys:**
  - OpenAI: https://platform.openai.com/api-keys (free tier: $5 credit)
  - Groq: https://console.groq.com/keys (free tier: 30 requests/minute)

### Option 1: Direct Local Setup (Recommended for Development)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/rag-engine.git
cd rag-engine

# 2. Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Create .env file with your API keys
cat > .env << EOF
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
GROQ_API_KEY=gsk_YOUR_KEY_HERE
EOF

# 5. Start backend server
cd backend
python main.py
# Or: uvicorn api.main:app --reload --port 8000
# ✓ Backend running on http://localhost:8000
# ✓ Swagger UI at http://localhost:8000/docs

# 6. Open NEW terminal for frontend
cd frontend
npm install
npm run dev
# ✓ Frontend running on http://localhost:3000

# 7. Open browser
open http://localhost:3000
```

### Option 2: Docker Compose (Production-like)

```bash
# 1. Clone and enter
git clone https://github.com/yourusername/rag-engine.git
cd rag-engine

# 2. Create .env file
cat > .env << EOF
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
GROQ_API_KEY=gsk_YOUR_KEY_HERE
EOF

# 3. Build and start
docker compose up --build

# 4. Open http://localhost:3000
# Backend: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

---

## 📖 How to Use

1. **Upload a PDF** (left sidebar)
   - Drag-drop or click to select
   - System extracts text, chunks, embeds, and stores in ChromaDB
   - Takes ~30 seconds for 50-page document

2. **Ask a Question** (center)
   - Type your question in the input box
   - Press Enter or click "Ask"
   - System routes to simple or complex path automatically

3. **Review Answer with Citations** (center + right sidebar)
   - Answer appears with inline `[C1]`, `[C2]` badges
   - Click any badge to highlight source in right panel
   - Panel shows: source file, page number, similarity score, rerank score

4. **Example Questions**
   - "What is S3?" (simple → direct retrieval)
   - "Compare S3 Standard vs S3 Infrequent Access" (complex → HyDE + rerank)
   - "What are the storage classes?" (simple)
   - "How does IAM work?" (complex)

---

## 🔌 API Endpoints

### POST /upload
Upload a PDF document.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -H "X-OpenAI-Key: sk-proj-..." \
  -H "X-Groq-Key: gsk_..."
```

**Response:**
```json
{
  "doc_id": "document.pdf",
  "pages": 46,
  "chunk_count": 791,
  "indexed_at": "2025-05-03T12:34:56Z"
}
```

### GET /documents
List all uploaded documents.

```bash
curl http://localhost:8000/documents \
  -H "X-OpenAI-Key: sk-proj-..." \
  -H "X-Groq-Key: gsk_..."
```

### GET /query/stream
Stream query results in real-time.

```bash
curl -N http://localhost:8000/query/stream \
  -G --data-urlencode "question=What is S3?" \
  -H "X-OpenAI-Key: sk-proj-..." \
  -H "X-Groq-Key: gsk_..."
```

**Response (Server-Sent Events):**
```
data: "S3"
data: " is"
data: " Amazon's"
...
data: {"answer": "...", "citations": [...], "route_taken": "simple", "latency_ms": 412}
```

### DELETE /documents/{doc_id}
Delete a document.

```bash
curl -X DELETE http://localhost:8000/documents/document.pdf \
  -H "X-OpenAI-Key: sk-proj-..." \
  -H "X-Groq-Key: gsk_..."
```

**Full API docs:** http://localhost:8000/docs (interactive Swagger UI)

---

## 📁 Project Structure

```
rag-engine/
│
├── backend/
│   ├── api/
│   │   ├── main.py                 # FastAPI application
│   │   ├── models.py               # Pydantic request/response schemas
│   │   ├── dependencies.py         # Dependency injection (API key resolution)
│   │   └── routes/
│   │       ├── upload.py           # POST /upload
│   │       ├── query.py            # GET /query/stream
│   │       └── documents.py        # GET/DELETE /documents
│   │
│   ├── generation/
│   │   ├── generator.py            # Token streaming via Groq
│   │   ├── prompts.py              # System prompts for LLM
│   │   └── schema.py               # RAGResponse dataclass
│   │
│   ├── retrieval/
│   │   ├── router.py               # Query classification (simple/complex)
│   │   ├── retriever.py            # ChromaDB vector search
│   │   ├── hyde.py                 # HyDE hypothetical answer generation
│   │   └── reranker.py             # MS MARCO cross-encoder reranking
│   │
│   ├── ingestion/
│   │   ├── pipeline.py             # Full document ingestion pipeline
│   │   ├── extractor.py            # PyMuPDF text extraction
│   │   ├── chunker.py              # LangChain recursive chunking
│   │   ├── embedder.py             # OpenAI embeddings with batching
│   │   ├── store.py                # ChromaDB persistence
│   │   └── logger.py               # Ingestion event logging
│   │
│   ├── Dockerfile                  # Multi-stage production image
│   ├── requirements.txt            # Python dependencies
│   └── main.py                     # Entry point
│
├── frontend/
│   ├── app/
│   │   ├── chat/page.tsx           # Main chat interface
│   │   ├── layout.tsx              # Root layout wrapper
│   │   ├── page.tsx                # Redirect to /chat
│   │   └── globals.css             # Global styles
│   │
│   ├── components/
│   │   ├── KeySetup.tsx            # API key entry screen (sessionStorage)
│   │   ├── AnswerDisplay.tsx       # Rendered answer with citations
│   │   ├── SourcesPanel.tsx        # Citation sources sidebar
│   │   ├── DocumentList.tsx        # Uploaded documents list
│   │   └── UploadZone.tsx          # Drag-drop PDF upload
│   │
│   ├── lib/
│   │   ├── api.ts                  # API client (auto-adds auth headers)
│   │   └── utils.ts                # Utility functions
│   │
│   ├── types/
│   │   └── index.ts                # TypeScript type definitions
│   │
│   ├── Dockerfile                  # Multi-stage production image
│   ├── next.config.ts              # Next.js config (standalone output)
│   ├── package.json                # Node dependencies
│   ├── tsconfig.json               # TypeScript config
│   └── tailwind.config.ts          # Tailwind CSS config
│
├── eval/
│   ├── run_eval.py                 # RAGAS evaluation script
│   ├── parameter_sweep.py          # Grid search over chunk configs
│   └── results/
│       ├── summary_scores.csv      # Benchmarked results table
│       └── run_*.csv               # Individual experiment logs
│
├── scripts/
│   ├── test_chunker.py             # Unit tests
│   ├── test_embedder.py
│   ├── test_extractor.py
│   ├── test_generation.py
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_router.py
│   └── test_streaming.py
│
├── docker-compose.yml              # Local dev environment
├── docker-compose.prod.yml         # AWS production environment
├── .env.example                    # Template (copy to .env)
├── .gitignore                      # Git exclusions
└── README.md                       # This file
```

---

## ⚙️ Configuration

### Winning Parameters (Benchmarked)

These values were validated with RAGAS and are production-ready:

```python
# backend/retrieval/router.py
SIMPLE_RETRIEVE_K = 8           # Direct retrieval top-k
COMPLEX_RETRIEVE_K = 24         # HyDE retrieval top-k before reranking
RERANK_TOP_N = 5                # Final reranked results

# backend/ingestion/chunker.py
CHUNK_SIZE = 1024               # Characters per chunk
CHUNK_OVERLAP = 32              # Character overlap between chunks
```

### Model Selection

| Component | Model | Reason |
|-----------|-------|--------|
| **Embeddings** | OpenAI text-embedding-3-small | High quality, low cost ($0.02/1M tokens) |
| **Generation** | Groq llama-3.3-70b-versatile | Free, fast (inference in 400-1300ms) |
| **Reranker** | MS MARCO MiniLM (local) | ~1.5GB, runs locally, prevents API calls |

### API Costs (Monthly Estimate)

```
OpenAI Embeddings:
  - 50 documents × 100 chunks × 500 tokens = 2.5M tokens
  - Cost: 2.5M × $0.02 / 1M = ~$0.05

Groq LLaMA:
  - Free tier: 30 requests/minute
  - Free tier cost: $0

AWS (if deploying):
  - EC2 t3.medium: ~$30/month (when running)
  - Data transfer: ~$0.09/GB
  
Total: $0.05/month (local) | $30-40/month (AWS)
```

---

## 📊 Evaluation Results

Validated with **RAGAS framework** on AWS Certified Solutions Architect slides (46 pages, 791 chunks).

```
Metric                  Score    Interpretation
─────────────────────────────────────────────────
Faithfulness            0.92     Claims closely match source material
Answer Relevancy        0.88     Answers directly address queries
Context Precision       0.91     Retrieved chunks are on-topic
Context Recall          0.89     All necessary information retrieved
─────────────────────────────────────────────────
Average                 0.90     Production-grade quality
```

**Configuration:** chunk_size=1024, overlap=32, k=8 (simple), k=24 (complex), rerank_top=5

See `eval/results/summary_scores.csv` for detailed experiment logs.

---

## 🔐 Security

✅ **No Server-Side Key Storage**
- User API keys stored in browser `sessionStorage` only
- Keys sent as request headers (`X-OpenAI-Key`, `X-Groq-Key`)
- Server never persists or logs keys

✅ **Per-User Authentication**
- Each user brings their own OpenAI + Groq keys
- Keys are isolated per session
- Session clears on tab close

✅ **No Data Leakage**
- Uploaded PDFs stored locally in ChromaDB
- No external logging or telemetry
- No third-party analytics

✅ **Defensive Streaming**
- Guards against Groq edge cases (empty choices, None content)
- Proper error handling and timeouts
- Graceful degradation on API failures

---

## 🐳 Docker & Deployment

### Local Docker Compose

```bash
docker compose up --build
# ✓ Backend: http://localhost:8000
# ✓ Frontend: http://localhost:3000
```

### Production: AWS EC2 + ECR

**1. Create ECR repositories:**
```bash
aws ecr create-repository --repository-name rag-engine-backend --region us-east-1
aws ecr create-repository --repository-name rag-engine-frontend --region us-east-1
```

**2. Push Docker images:**
```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker tag rag-engine-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rag-engine-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rag-engine-backend:latest

docker tag rag-engine-frontend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rag-engine-frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rag-engine-frontend:latest
```

**3. Launch EC2 & deploy:**
```bash
# Launch t3.medium Ubuntu 24.04 instance
# Update docker-compose.prod.yml with your account ID
# SCP files to EC2
# Run: docker compose -f docker-compose.prod.yml up -d
```

**Cost:** ~$30-40/month (EC2) + OpenAI usage (user-provided keys)

---

## 📝 Interview Talking Points

**"I built a production-grade RAG system that demonstrates end-to-end ML engineering:"**

1. **Intelligent Retrieval** — Query router automatically selects between direct search and HyDE+reranking based on complexity

2. **Real-Time Streaming** — Token-by-token generation via Server-Sent Events for responsive UX

3. **Citation System** — Every answer claim tagged with source file, page number, and relevance scores

4. **Optimization** — Benchmarked with RAGAS framework; achieved 0.90 average score through parameter tuning

5. **Security** — User API keys stored in browser sessionStorage, never on server; full TypeScript type safety

6. **Docker Ready** — Multi-stage production builds (~500MB images) with health checks and graceful degradation

7. **Trade-offs** — Chose Groq (free, fast) over OpenAI for generation; ChromaDB (local, persistent) over Pinecone; EC2 over Lambda (keeps cross-encoder warm)

---

## 🚀 Future Enhancements

- [ ] User authentication (Auth0/Firebase)
- [ ] Payment processing (Stripe) for public SaaS model
- [ ] Rate limiting and quota management per user
- [ ] HTTPS, custom domain, DNS routing
- [ ] Advanced analytics (query latency heatmap, cost attribution)
- [ ] Multi-document Q&A (cross-document reasoning)
- [ ] Fine-tuned reranker on proprietary data
- [ ] Mobile app (React Native)

---

## 📚 Resources

- **Groq API Docs:** https://console.groq.com/docs/
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings
- **ChromaDB:** https://docs.trychroma.com/
- **RAGAS:** https://docs.ragas.io/
- **LangChain:** https://python.langchain.com/

---

## 📄 License

MIT — Free to use, modify, and distribute.

---

## 🤝 Contributing

This is a portfolio project. Feel free to fork, extend, and share improvements!

---

## 💬 Questions?

1. **How to run?** → See [Quick Start](#-quick-start)
2. **API docs?** → http://localhost:8000/docs
3. **How does routing work?** → See [Architecture](#-architecture)
4. **What are the costs?** → See [Configuration](#-configuration)
5. **How to deploy?** → See [Docker & Deployment](#-docker--deployment)

---

**Built with ❤️ by Kushal | Portfolio Project | May 2025**