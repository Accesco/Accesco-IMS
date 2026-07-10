"""
Tests for the Replenishment module.

Covers:
- Recommendation CRUD lifecycle
- Status transitions (approve, reject, convert)
- ML client error handling (mocked httpx calls)
- PO creation from approved recommendation
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.models.product import Product
from app.models.inventory import InventoryItem
from app.models.replenishment import ReplenishmentRecommendation
from app.modules.replenishment.service import ReplenishmentService
from app.modules.replenishment.repository import ReplenishmentRepository
from app.modules.replenishment.ml_client import build_ml_payload, call_ml_engine
from app.core.exceptions import ResourceNotFoundException, IMSException, MLServiceUnavailableException


# ─── ML Client Tests ───────────────────────────────────────────────


class TestBuildMLPayload:
    """Test the IMS → ML payload transformation logic."""

    def test_basic_payload(self):
        payload = build_ml_payload(
            sku_id="ACS-12345",
            on_hand=10,
            reserved=2,
        )
        assert payload["sku_id"] == "ACS-12345"
        assert payload["On_Hand"] == 10
        assert payload["Reserved"] == 2
        assert payload["Daily_Velocity"] == 5.0  # Default
        # Default to Ambient when no zone specified
        assert payload["Temp_Zone_Ambient"] == 1
        assert payload["Temp_Zone_Chilled"] == 0
        assert payload["Temp_Zone_Frozen"] == 0

    def test_store_one_hot_encoding(self):
        payload = build_ml_payload(
            sku_id="ACS-001",
            on_hand=5,
            reserved=0,
            store_name="DS_BLR_02",
        )
        assert payload["Dark_Store_ID_DS_BLR_01"] == 0
        assert payload["Dark_Store_ID_DS_BLR_02"] == 1
        assert payload["Dark_Store_ID_DS_BLR_03"] == 0

    def test_temp_zone_chilled(self):
        payload = build_ml_payload(
            sku_id="ACS-002",
            on_hand=3,
            reserved=1,
            temp_zone="Chilled",
        )
        assert payload["Temp_Zone_Ambient"] == 0
        assert payload["Temp_Zone_Chilled"] == 1
        assert payload["Temp_Zone_Frozen"] == 0

    def test_custom_velocity(self):
        payload = build_ml_payload(
            sku_id="ACS-003",
            on_hand=1,
            reserved=0,
            daily_velocity=15.5,
        )
        assert payload["Daily_Velocity"] == 15.5


# ─── ML Client HTTP Tests ──────────────────────────────────────────


class TestCallMLEngine:
    """Test ML engine HTTP calls with mocked httpx."""

    @pytest.mark.asyncio
    async def test_successful_reorder_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "event_type": "AUTOMATED_PO_TRIGGERED",
            "confidence_score": 0.95,
            "action": "GENERATE_PURCHASE_ORDER",
            "kafka_status": "published",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.modules.replenishment.ml_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await call_ml_engine({"sku_id": "ACS-001", "On_Hand": 1})
            assert result["event_type"] == "AUTOMATED_PO_TRIGGERED"
            assert result["confidence_score"] == 0.95

    @pytest.mark.asyncio
    async def test_healthy_stock_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "Inventory levels stable.",
            "kafka_status": "no_event",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.modules.replenishment.ml_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await call_ml_engine({"sku_id": "ACS-002", "On_Hand": 50})
            assert result.get("event_type") is None
            assert result["status"] == "Inventory levels stable."

    @pytest.mark.asyncio
    async def test_connection_error_raises_503(self):
        import httpx

        with patch("app.modules.replenishment.ml_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.ConnectError("Connection refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            with pytest.raises(MLServiceUnavailableException):
                await call_ml_engine({"sku_id": "ACS-003"})

    @pytest.mark.asyncio
    async def test_timeout_raises_503(self):
        import httpx

        with patch("app.modules.replenishment.ml_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.ReadTimeout("Timed out")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            with pytest.raises(MLServiceUnavailableException):
                await call_ml_engine({"sku_id": "ACS-004"})


# ─── Repository Tests ──────────────────────────────────────────────


class TestReplenishmentRepository:
    """Test DB operations for recommendations."""

    @pytest.mark.asyncio
    async def test_create_and_get_recommendation(self, db_session: AsyncSession):
        # Setup: create a store and product
        store = Store(name="Test Store", address="123 St", city="BLR", state="KA")
        product = Product(sku="ACS-TEST-001", name="Test Product", category="Ambient", unit="unit")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)
        rec = await repo.create_recommendation(
            store_id=store.id,
            product_id=product.id,
            sku_id="ACS-TEST-001",
            recommended_quantity=25,
            confidence_score=0.92,
            ml_response_payload={"event_type": "AUTOMATED_PO_TRIGGERED"},
        )

        assert rec.id is not None
        assert rec.status == "PENDING"
        assert rec.confidence_score == 0.92

        # Get by ID
        fetched = await repo.get_recommendation_by_id(rec.id)
        assert fetched is not None
        assert fetched.sku_id == "ACS-TEST-001"

    @pytest.mark.asyncio
    async def test_get_recommendations_filtered(self, db_session: AsyncSession):
        store = Store(name="Filter Store", address="456 St", city="BLR", state="KA")
        product = Product(sku="ACS-FILT-001", name="Filter Product", category="Chilled", unit="kg")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)

        # Create two recommendations with different statuses
        rec1 = await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-FILT-001",
            recommended_quantity=10, confidence_score=0.85,
        )
        await repo.update_recommendation_status(rec1, "APPROVED")

        await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-FILT-001",
            recommended_quantity=20, confidence_score=0.90,
        )

        # Filter by status
        pending = await repo.get_recommendations(store_id=store.id, status="PENDING")
        assert len(pending) == 1
        assert pending[0].recommended_quantity == 20

        approved = await repo.get_recommendations(store_id=store.id, status="APPROVED")
        assert len(approved) == 1
        assert approved[0].recommended_quantity == 10

    @pytest.mark.asyncio
    async def test_status_transition(self, db_session: AsyncSession):
        store = Store(name="Status Store", address="789 St", city="BLR", state="KA")
        product = Product(sku="ACS-STAT-001", name="Status Product", category="Frozen", unit="pack")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)
        rec = await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-STAT-001",
            recommended_quantity=15, confidence_score=0.88,
        )

        assert rec.status == "PENDING"

        await repo.update_recommendation_status(rec, "APPROVED")
        assert rec.status == "APPROVED"

        await repo.link_purchase_order(rec, 999)
        assert rec.status == "CONVERTED"
        assert rec.purchase_order_id == 999

    @pytest.mark.asyncio
    async def test_get_nonexistent_recommendation(self, db_session: AsyncSession):
        repo = ReplenishmentRepository(db_session)
        result = await repo.get_recommendation_by_id(99999)
        assert result is None


# ─── Service Tests ──────────────────────────────────────────────────


class TestReplenishmentService:
    """Test business logic and status validation."""

    @pytest.mark.asyncio
    async def test_approve_pending_recommendation(self, db_session: AsyncSession):
        store = Store(name="Svc Store", address="Svc Addr", city="BLR", state="KA")
        product = Product(sku="ACS-SVC-001", name="Svc Product", category="Ambient", unit="unit")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)
        rec = await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-SVC-001",
            recommended_quantity=30, confidence_score=0.95,
        )
        await db_session.commit()

        service = ReplenishmentService(db_session)
        approved = await service.approve_recommendation(rec.id)
        assert approved.status == "APPROVED"

    @pytest.mark.asyncio
    async def test_reject_pending_recommendation(self, db_session: AsyncSession):
        store = Store(name="Rej Store", address="Rej Addr", city="BLR", state="KA")
        product = Product(sku="ACS-REJ-001", name="Rej Product", category="Ambient", unit="unit")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)
        rec = await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-REJ-001",
            recommended_quantity=20, confidence_score=0.80,
        )
        await db_session.commit()

        service = ReplenishmentService(db_session)
        rejected = await service.reject_recommendation(rec.id)
        assert rejected.status == "REJECTED"

    @pytest.mark.asyncio
    async def test_cannot_approve_non_pending(self, db_session: AsyncSession):
        store = Store(name="Inv Store", address="Inv Addr", city="BLR", state="KA")
        product = Product(sku="ACS-INV-001", name="Inv Product", category="Ambient", unit="unit")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)
        rec = await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-INV-001",
            recommended_quantity=10, confidence_score=0.75,
        )
        await repo.update_recommendation_status(rec, "REJECTED")
        await db_session.commit()

        service = ReplenishmentService(db_session)
        with pytest.raises(IMSException):
            await service.approve_recommendation(rec.id)

    @pytest.mark.asyncio
    async def test_cannot_convert_non_approved(self, db_session: AsyncSession):
        store = Store(name="Conv Store", address="Conv Addr", city="BLR", state="KA")
        product = Product(sku="ACS-CONV-001", name="Conv Product", category="Ambient", unit="unit")
        db_session.add_all([store, product])
        await db_session.flush()

        repo = ReplenishmentRepository(db_session)
        rec = await repo.create_recommendation(
            store_id=store.id, product_id=product.id, sku_id="ACS-CONV-001",
            recommended_quantity=40, confidence_score=0.99,
        )
        await db_session.commit()

        service = ReplenishmentService(db_session)
        with pytest.raises(IMSException):
            await service.convert_to_purchase_order(rec.id)  # Status is PENDING, not APPROVED

    @pytest.mark.asyncio
    async def test_get_nonexistent_recommendation_raises_404(self, db_session: AsyncSession):
        service = ReplenishmentService(db_session)
        with pytest.raises(ResourceNotFoundException):
            await service.get_recommendation_by_id(99999)
