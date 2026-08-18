# VersusAI — Product Intelligence & Comparison Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=flat-square&logo=chroma&logoColor=white)](https://www.trychroma.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Flash_LLM-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**VersusAI** (built for Cognizant CTS Hackathon) is a **Hybrid RAG & LLM-powered Product Intelligence, Comparison & Recommendation Platform**. It couples relational ground-truth databases (AWS RDS MySQL / SQLite) with semantic vector search (ChromaDB) to deliver accurate, hallucination-free product analysis.

---

## ⚡ Key Features

- **Dual-Engine Grounding:** Combines deterministic SQL specs (pricing, RAM, CPU, battery) with ChromaDB semantic search (manuals, thermals, user guides).
- **AI Product Battle Arena:** Head-to-head showdowns with 5-factor weighted scoring (Performance 40%, Value 20%, Display 15%, Battery 10%, Rating 15%) and AI Judge verdicts.
- **Context-Aware AI Chat:** Multi-turn conversational memory, intent classification, dynamic follow-up suggestions, and rich spec cards.
- **RAG VER2 Document Intelligence:** PDF manual upload, semantic section chunking, multi-factor reranking, and citation-backed generation.
- **Recommendation & Comparison Matrix:** Use-case suitability scoring (Gaming, Productivity, Creator, Budget) and side-by-side spec diffs with 1-click PDF export.
- **Real-Time Notifications:** Live WebSocket server (`/ws/notifications`) for battle outcomes, price alerts, and system events.
- **Multi-Category Catalog:** Unified schema supporting **Laptops**, **Smartphones**, and **Tablets** with automated CSV ingestion.
- **Resilient Fallback:** Automatic failover from AWS RDS MySQL to local SQLite for offline resilience.

---

## 🛠 Tech Stack

- **Frontend:** Next.js 16 (React 19, TypeScript), Tailwind CSS v4, Framer Motion, Recharts, Lucide Icons, jsPDF.
- **Backend:** FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, PyMySQL / SQLite, PyJWT, WebSockets.
- **AI / Vector Store:** ChromaDB, Sentence-Transformers (`all-MiniLM-L6-v2`), Google Gemini Flash LLM.

---

## 🚀 Quickstart Guide

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                             # Add your GEMINI LLM_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
> API running at `http://localhost:8000` | Interactive Docs: `http://localhost:8000/docs`

### 2. Frontend (Next.js 16)

```bash
cd frontend/my-app
npm install
cp .env.example .env.local                       # NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm run dev
```
> Web App running at `http://localhost:3000`

### 3. Production Docker & AWS EC2 Deployment

```bash
cp .env.production.example .env                  # Add your AWS RDS MySQL & Gemini API keys
chmod +x deploy-aws-ec2.sh
./deploy-aws-ec2.sh
```
> Full step-by-step AWS guide (RDS MySQL, EC2, Nginx, Let's Encrypt SSL): see [AWS_DEPLOYMENT_GUIDE.md](file:///Users/asf28146gmail.com/Desktop/cts%20project/AWS_DEPLOYMENT_GUIDE.md)

---

## ⚙️ Key Environment Variables (`backend/.env`)

```env
LLM_API_KEY=your_google_gemini_api_key
DATABASE_URL=mysql+pymysql://admin:password@host:3306/my_project?charset=utf8mb4
JWT_SECRET=your_secret_key
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## 🔌 API & Testing Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Conversational query with session memory & RAG context |
| `POST` | `/api/battle` | AI Battle Arena simulation & 5-dimension scoring |
| `POST` | `/api/compare` | Multi-product side-by-side comparison matrix |
| `POST` | `/api/recommendations` | Weighted use-case & budget recommendations |
| `POST` | `/api/documents/upload` | PDF datasheet upload & vector indexing |
| `WS`   | `/ws/notifications` | Real-time push notification WebSocket stream |

```bash
# Run Automated Tests (from backend/):
python test_complete_ai_chat_pipeline.py
python test_product_battle.py
python test_advanced_rag_quality.py
```

---

## 📄 License

MIT License • Built for Cognizant (CTS) Hackathon.
