from __future__ import annotations
import uvicorn
from app.config import settings

if __name__ == "__main__":
    # ARCHITECTURAL FIX: Use configured host/port instead of hardcoded values
    uvicorn.run(
        "app.main:app", 
        host=settings.app_host, 
        port=settings.app_port, 
        reload=False, 
        access_log=settings.log_enable
    )