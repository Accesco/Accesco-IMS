# Accesco Living - Dark Store Inventory Management System (IMS)

Accesco Living IMS is a high-performance, modular monolith backend service for dark store inventory management. It manages store inventory levels, customer orders, stock reservations, background procurement, and payment webhooks.

## Architecture Overview

Accesco Living IMS follows a **Modular Monolith** architecture with strict separation between API, Service, Repository, and Infrastructure layers.

```
app/
├── main.py                 # Application Entrypoint & Startup Lifecycles
├── api/
│   └── v1/                 # API Router Aggregation
├── core/                   # Core modules (config, security, database, redis, kafka, events, exceptions)
├── models/                 # Shared SQLAlchemy Database Models
├── schemas/                # Shared Schemas (if any, module schemas are inside their folders)
├── modules/                # Business Domain Modules
│   ├── auth/               # User registration, Login, and RBAC
│   ├── stores/             # Dark store CRUD
│   ├── products/           # Product Catalog
│   ├── inventory/          # Row-locking Stock Reservations & Updates
│   ├── cart/               # Redis-based shopping carts
│   ├── orders/             # Order placement & cancellations
│   ├── payments/           # Razorpay Checkout & Webhook handler
│   └── procurement/        # Purchase orders and automatic reordering
├── workers/                # Background process consumers
│   ├── kafka_consumer.py   # Processes async events from Kafka topics
│   ├── outbox_processor.py # Durability layer publishing DB events to Kafka
│   └── reservation_sweeper.py # Sweeps and releases expired reservations
├── migrations/             # Alembic migration scripts
└── scripts/                # Database seed scripts
```

### Core Design Rules
* **PostgreSQL** is the primary source of truth.
* **Redis** is used for caching, shopping carts, and temporary inventory states.
* **Apache Kafka** handles event-driven communications.
* **Transactional Outbox Pattern** ensures database updates and corresponding Kafka messages are committed atomically.
* **Row-Level Locking** (`SELECT ... FOR UPDATE`) is enforced during reservations to prevent negative stock conditions under high concurrency.
* **Dependency Injection** is used via FastAPI's `Depends` mechanisms. All database accesses occur strictly within Repository classes.

---

## Tech Stack

* **Language**: Python 3.12
* **Framework**: FastAPI
* **Server**: Uvicorn
* **Database**: PostgreSQL 16 (via SQLAlchemy 2.0 Async + asyncpg)
* **Migrations**: Alembic
* **Caching/Temporary State**: Redis (async redis-py)
* **Messaging**: Apache Kafka (aiokafka)
* **Auth**: JWT (python-jose + passlib with bcrypt)
* **Payments**: Razorpay Integration
* **Containerization**: Docker Compose

---

## Kafka Event Flows

| Topic | Emitted By | Triggered By | Consumed By | Worker Logic |
| :--- | :--- | :--- | :--- | :--- |
| `orders.placed` | Orders Module | Order Placement | - | Dashboard/Metrics logging |
| `payments.confirmed` | Payments Module | Razorpay webhook validation | Kafka Consumer | Confirms order, checks inventory, reserves stock (row-level locking), and emits `inventory.reserved` |
| `inventory.reserved` | Inventory Module | Reservation creation | - | Auditing/Fulfillment |
| `inventory.updated` | Inventory/Procurement | Manual stock addition / PO reception | - | Stock reconciliation |
| `inventory.low` | Inventory Module | Available stock <= reorder level | Kafka Consumer | Automatically generates draft Purchase Order and emits `procurement.created` |
| `inventory.released` | Inventory Module | Reservation cancel/expiry | - | Stock restore logging |
| `procurement.created` | Procurement Module | PO generation | - | Supplier alerting |
| `orders.cancelled` | Orders Module | Order cancellation | Kafka Consumer | Identifies reservations for order, releases locks, restores available stock, and emits `inventory.released` |

---

## Local Setup Instructions

### Prerequisites
* Python 3.12+
* Docker & Docker Compose
* Make (optional, but convenient)

### 1. Clone & Configure Environment
Create a copy of `.env.example` as `.env` and adjust the variables if needed:
```bash
cp .env.example .env
```

### 2. Launch Infrastructure Services
Start the database, caching, messaging, and administration services in the background:
```bash
docker-compose up -d
```
This spins up:
* **PostgreSQL** on port `5432`
* **Redis** on port `6379`
* **Zookeeper & Apache Kafka** on port `9092`
* **PgAdmin** on port `5050` (Login: `admin@accesco.com` / `admin`)

### 3. Install Python Dependencies
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Database Migrations & Seeding
Initialize the database tables and apply initial seed data (roles, stores, products, inventory, admin user):
```bash
# Run migrations
alembic upgrade head

# Seed the database
python -m app.scripts.seed
```
*Default Seeded Credentials:*
* **Admin Username**: `admin`
* **Admin Password**: `adminpassword`

---

## Running the Application

### Using Makefile
If you have `make` installed:
```bash
# Start the FastAPI Web Server (live-reload enabled)
make dev

# Run test suites
make test

# Code quality checks
make lint
```

### Running Manually
```bash
# Web Application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Kafka Consumer Worker
python -m app.workers.kafka_consumer

# Outbox Processor Worker
python -m app.workers.outbox_processor

# Reservation Expiry Sweeper
python -m app.workers.reservation_sweeper
```

The Interactive API documentation is available at `http://localhost:8000/docs` (Swagger UI).

---

## Testing

Tests are written using `pytest` and `pytest-asyncio`. A clean in-memory SQLite database is generated for each test run to ensure isolated execution of:
* User registration, logins, and JWT validation
* Negative stock prevention & concurrency locking logic
* Order placement and outbox record validation
* Kafka consumer handlers (`payments.confirmed`, `inventory.low`, `orders.cancelled`)

Run tests:
```bash
pytest -v --asyncio-mode=strict
```
