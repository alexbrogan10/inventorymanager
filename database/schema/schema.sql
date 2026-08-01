-- Reference schema for the AI Inventory Management System.
--
-- This is documentation, not the source of truth: the real schema history is
-- the Alembic migrations in backend/alembic/versions/, generated from the
-- SQLAlchemy models in backend/app/models/. This file exists for anyone who
-- wants to read the data model as plain SQL without running the app or a
-- migration tool. If it and the migrations ever disagree, the migrations win
-- - regenerate this file from `pg_dump --schema-only` against a freshly
-- migrated database rather than hand-editing it out of sync.
--
-- Generated against PostgreSQL 16, matching migrations through
-- 3ee505a4c83c_add_notifications.py (Milestone 14).

-- === Enums ===

CREATE TYPE user_role AS ENUM ('admin', 'manager', 'employee');
CREATE TYPE purchase_order_status AS ENUM ('ordered', 'shipped', 'received', 'cancelled');
CREATE TYPE notification_type AS ENUM ('low_stock', 'overstock', 'order_arrived', 'anomaly');
CREATE TYPE notification_severity AS ENUM ('info', 'warning', 'critical');

-- === Users & RBAC (Milestone 2) ===

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'employee',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_email ON users (email);

-- === Catalog (Milestone 3-4) ===

CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_categories_name ON categories (name);

CREATE TABLE suppliers (
    id              SERIAL PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL UNIQUE,
    contact_person  VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    phone           VARCHAR(50) NOT NULL,
    address         TEXT NOT NULL,
    lead_time_days  INTEGER NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_suppliers_company_name ON suppliers (company_name);

CREATE TABLE products (
    id                SERIAL PRIMARY KEY,
    sku               VARCHAR(64) NOT NULL UNIQUE,
    barcode           VARCHAR(64) UNIQUE,
    name              VARCHAR(255) NOT NULL,
    description       TEXT,
    category_id       INTEGER NOT NULL REFERENCES categories (id),
    supplier_id       INTEGER NOT NULL REFERENCES suppliers (id),
    purchase_price    NUMERIC(10, 2) NOT NULL,
    selling_price     NUMERIC(10, 2) NOT NULL,
    minimum_quantity  INTEGER NOT NULL DEFAULT 0,
    maximum_quantity  INTEGER,
    unit_type         VARCHAR(50) NOT NULL DEFAULT 'each',
    image_url         VARCHAR(512),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_products_sku ON products (sku);
CREATE INDEX ix_products_barcode ON products (barcode);
CREATE INDEX ix_products_name ON products (name);
CREATE INDEX ix_products_category_id ON products (category_id);
CREATE INDEX ix_products_supplier_id ON products (supplier_id);

-- === Warehouses & multi-location inventory (Milestone 5) ===

CREATE TABLE warehouses (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    address     TEXT NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_warehouses_name ON warehouses (name);

CREATE TABLE inventory_levels (
    id            SERIAL PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products (id),
    warehouse_id  INTEGER NOT NULL REFERENCES warehouses (id),
    quantity      INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_inventory_product_warehouse UNIQUE (product_id, warehouse_id)
);
CREATE INDEX ix_inventory_levels_product_id ON inventory_levels (product_id);
CREATE INDEX ix_inventory_levels_warehouse_id ON inventory_levels (warehouse_id);

CREATE TABLE inventory_transfers (
    id                  SERIAL PRIMARY KEY,
    product_id          INTEGER NOT NULL REFERENCES products (id),
    from_warehouse_id   INTEGER NOT NULL REFERENCES warehouses (id),
    to_warehouse_id     INTEGER NOT NULL REFERENCES warehouses (id),
    quantity            INTEGER NOT NULL,
    transferred_by_id   INTEGER NOT NULL REFERENCES users (id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_inventory_transfers_product_id ON inventory_transfers (product_id);
CREATE INDEX ix_inventory_transfers_from_warehouse_id ON inventory_transfers (from_warehouse_id);
CREATE INDEX ix_inventory_transfers_to_warehouse_id ON inventory_transfers (to_warehouse_id);

-- === Purchase orders (Milestone 6) ===

CREATE TABLE purchase_orders (
    id                      SERIAL PRIMARY KEY,
    supplier_id             INTEGER NOT NULL REFERENCES suppliers (id),
    warehouse_id            INTEGER NOT NULL REFERENCES warehouses (id),
    status                  purchase_order_status NOT NULL DEFAULT 'ordered',
    expected_delivery_date  DATE,
    notes                   TEXT,
    created_by_id           INTEGER NOT NULL REFERENCES users (id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_purchase_orders_supplier_id ON purchase_orders (supplier_id);
CREATE INDEX ix_purchase_orders_warehouse_id ON purchase_orders (warehouse_id);
CREATE INDEX ix_purchase_orders_status ON purchase_orders (status);
CREATE INDEX ix_purchase_orders_created_by_id ON purchase_orders (created_by_id);

CREATE TABLE purchase_order_items (
    id                  SERIAL PRIMARY KEY,
    purchase_order_id   INTEGER NOT NULL REFERENCES purchase_orders (id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES products (id),
    quantity_ordered    INTEGER NOT NULL,
    unit_cost           NUMERIC(10, 2) NOT NULL,
    quantity_received   INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_purchase_order_items_purchase_order_id ON purchase_order_items (purchase_order_id);
CREATE INDEX ix_purchase_order_items_product_id ON purchase_order_items (product_id);

-- === Sales (Milestone 7) ===

CREATE TABLE sales (
    id              SERIAL PRIMARY KEY,
    warehouse_id    INTEGER NOT NULL REFERENCES warehouses (id),
    customer_name   VARCHAR(255) NOT NULL,
    customer_email  VARCHAR(255),
    customer_phone  VARCHAR(50),
    notes           TEXT,
    sold_by_id      INTEGER NOT NULL REFERENCES users (id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_sales_warehouse_id ON sales (warehouse_id);
CREATE INDEX ix_sales_sold_by_id ON sales (sold_by_id);

CREATE TABLE sale_items (
    id          SERIAL PRIMARY KEY,
    sale_id     INTEGER NOT NULL REFERENCES sales (id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products (id),
    quantity    INTEGER NOT NULL,
    unit_price  NUMERIC(10, 2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_sale_items_sale_id ON sale_items (sale_id);
CREATE INDEX ix_sale_items_product_id ON sale_items (product_id);

-- === Notifications (Milestone 14) ===

CREATE TABLE notifications (
    id                  SERIAL PRIMARY KEY,
    type                notification_type NOT NULL,
    severity            notification_severity NOT NULL,
    title               VARCHAR(200) NOT NULL,
    message             VARCHAR(500) NOT NULL,
    product_id          INTEGER REFERENCES products (id),
    purchase_order_id   INTEGER REFERENCES purchase_orders (id),
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_notifications_type ON notifications (type);
CREATE INDEX ix_notifications_product_id ON notifications (product_id);
CREATE INDEX ix_notifications_purchase_order_id ON notifications (purchase_order_id);
CREATE INDEX ix_notifications_is_read ON notifications (is_read);
