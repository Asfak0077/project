# DEPRECATION NOTICE: `laptop_comparison_rag`

> [!WARNING]
> This folder (`laptop_comparison_rag`) is **DEPRECATED**. 
> The application has been fully migrated to use the centralized, multi-category **`rag/ver2`** pipeline (`new rag/ver2`).

## Active RAG Implementation Details:
- **Active RAG Location:** `rag/ver2` (`new rag/ver2`)
- **Centralized Service Bridge:** `backend/services/rag_service.py`
- **Vector Database:** `new rag/ver2/data/vector_db`
- **Supported Collections:** `laptops` (2,460 items), `mobiles` (5,583 items), `tablets` (820 items)
- **Active RAG Version:** `"ver2"`
- **Health Check Endpoint:** `GET /api/rag/health`

Do not add new code or active endpoints referencing `laptop_comparison_rag`. All future RAG enhancements must be added strictly to `rag/ver2`.
