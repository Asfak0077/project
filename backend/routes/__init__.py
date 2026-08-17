from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.products import router as products_router
from routes.compare import router as compare_router
from routes.recommendations import router as recommendations_router
from routes.chat import router as chat_router
from routes.favorites import router as favorites_router
from routes.history import router as history_router
from routes.documents import router as documents_router
from routes.feedback import router as feedback_router
from routes.admin import router as admin_router
from routes.dashboard import router as dashboard_router
from routes.session import router as session_router

__all__ = [
    "auth_router",
    "users_router",
    "products_router",
    "compare_router",
    "recommendations_router",
    "chat_router",
    "favorites_router",
    "history_router",
    "documents_router",
    "feedback_router",
    "admin_router",
    "dashboard_router",
    "session_router",
]
