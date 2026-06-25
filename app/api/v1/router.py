# app/api/v1/router.py
from fastapi import APIRouter

# Import your existing routers
from app.modules.auth.routes import router as auth_router
from app.modules.stores.routes import router as stores_router
from app.modules.products.routes import router as products_router
from app.modules.inventory.routes import router as inventory_router
from app.modules.cart.routes import router as cart_router
from app.modules.orders.routes import router as orders_router
from app.modules.payments.routes import router as payments_router
from app.modules.procurement.routes import router as procurement_router
from app.modules.riders.routes import router as riders_router
from app.modules.dispatch.routes import router as dispatch_router

# Phase 2 Addition: Import Communities Router
from app.modules.communities.routes import router as communities_router
from app.modules.audit.routes import router as audit_router

api_router = APIRouter()

# Include existing routers
api_router.include_router(auth_router)
api_router.include_router(stores_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(cart_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)
api_router.include_router(procurement_router)
api_router.include_router(riders_router)
api_router.include_router(dispatch_router)

# Phase 2 Addition: Include Communities Router
api_router.include_router(communities_router)
api_router.include_router(audit_router)