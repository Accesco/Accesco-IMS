from fastapi import APIRouter

# Import all module routers
from app.modules.auth.routes import router as auth_router
from app.modules.stores.routes import router as stores_router
from app.modules.products.routes import router as products_router
from app.modules.inventory.routes import router as inventory_router
from app.modules.cart.routes import router as cart_router
from app.modules.orders.routes import router as orders_router
from app.modules.payments.routes import router as payments_router
from app.modules.procurement.routes import router as procurement_router

api_router = APIRouter()

# Mount all endpoints under API v1
api_router.include_router(auth_router)
api_router.include_router(stores_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(cart_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)
api_router.include_router(procurement_router)
