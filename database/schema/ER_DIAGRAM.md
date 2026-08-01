# Entity-Relationship Diagram

Generated from the SQLAlchemy models in `backend/app/models/` (see
[`schema.sql`](./schema.sql) for the same model as plain SQL DDL). Renders
natively wherever GitHub or an Artifact viewer supports Mermaid.

```mermaid
erDiagram
    USERS ||--o{ PURCHASE_ORDERS : "created_by"
    USERS ||--o{ SALES : "sold_by"
    USERS ||--o{ INVENTORY_TRANSFERS : "transferred_by"

    CATEGORIES ||--o{ PRODUCTS : "categorizes"
    SUPPLIERS ||--o{ PRODUCTS : "supplies"
    SUPPLIERS ||--o{ PURCHASE_ORDERS : "fulfills"

    WAREHOUSES ||--o{ INVENTORY_LEVELS : "stocks"
    WAREHOUSES ||--o{ PURCHASE_ORDERS : "receives at"
    WAREHOUSES ||--o{ SALES : "sold from"
    WAREHOUSES ||--o{ INVENTORY_TRANSFERS : "ships from"
    WAREHOUSES ||--o{ INVENTORY_TRANSFERS : "receives into"

    PRODUCTS ||--o{ INVENTORY_LEVELS : "stocked as"
    PRODUCTS ||--o{ INVENTORY_TRANSFERS : "moved"
    PRODUCTS ||--o{ PURCHASE_ORDER_ITEMS : "ordered as"
    PRODUCTS ||--o{ SALE_ITEMS : "sold as"
    PRODUCTS ||--o{ NOTIFICATIONS : "triggers"

    PURCHASE_ORDERS ||--|{ PURCHASE_ORDER_ITEMS : "contains"
    PURCHASE_ORDERS ||--o{ NOTIFICATIONS : "triggers"

    SALES ||--|{ SALE_ITEMS : "contains"

    USERS {
        int id PK
        string email UK
        string hashed_password
        string full_name
        enum role "admin | manager | employee"
        bool is_active
    }

    CATEGORIES {
        int id PK
        string name UK
        text description
    }

    SUPPLIERS {
        int id PK
        string company_name UK
        string contact_person
        string email
        string phone
        text address
        int lead_time_days
        text notes
    }

    PRODUCTS {
        int id PK
        string sku UK
        string barcode UK
        string name
        text description
        int category_id FK
        int supplier_id FK
        numeric purchase_price
        numeric selling_price
        int minimum_quantity
        int maximum_quantity
        string unit_type
        string image_url
    }

    WAREHOUSES {
        int id PK
        string name UK
        text address
        text notes
    }

    INVENTORY_LEVELS {
        int id PK
        int product_id FK
        int warehouse_id FK
        int quantity
    }

    INVENTORY_TRANSFERS {
        int id PK
        int product_id FK
        int from_warehouse_id FK
        int to_warehouse_id FK
        int quantity
        int transferred_by_id FK
    }

    PURCHASE_ORDERS {
        int id PK
        int supplier_id FK
        int warehouse_id FK
        enum status "ordered | shipped | received | cancelled"
        date expected_delivery_date
        text notes
        int created_by_id FK
    }

    PURCHASE_ORDER_ITEMS {
        int id PK
        int purchase_order_id FK
        int product_id FK
        int quantity_ordered
        numeric unit_cost
        int quantity_received
    }

    SALES {
        int id PK
        int warehouse_id FK
        string customer_name
        string customer_email
        string customer_phone
        text notes
        int sold_by_id FK
    }

    SALE_ITEMS {
        int id PK
        int sale_id FK
        int product_id FK
        int quantity
        numeric unit_price
    }

    NOTIFICATIONS {
        int id PK
        enum type "low_stock | overstock | order_arrived | anomaly"
        enum severity "info | warning | critical"
        string title
        string message
        int product_id FK "nullable"
        int purchase_order_id FK "nullable"
        bool is_read
    }
```

## Reading notes

- **`PRODUCTS` has no direct quantity column.** Stock moved into
  `INVENTORY_LEVELS` in Milestone 5 (one row per product/warehouse pair,
  unique on that pair) once multiple warehouses existed; a product's total
  stock is the sum of its `INVENTORY_LEVELS.quantity` across warehouses.
  `minimum_quantity`/`maximum_quantity` stay on `PRODUCTS` because reorder
  policy is a property of the product, not of any one warehouse.
- **`PURCHASE_ORDER_ITEMS`/`SALE_ITEMS` snapshot price at the time of the
  transaction** (`unit_cost`/`unit_price`), not a live reference to
  `PRODUCTS.purchase_price`/`selling_price` — so historical reports never
  drift if the catalog price changes later.
- **`INVENTORY_TRANSFERS` is an append-only audit log**, never updated or
  deleted, doubling as the data source for the product movement report
  (Milestone 10).
- **`NOTIFICATIONS`** links to *either* a product (`low_stock`, `overstock`,
  `anomaly`) *or* a purchase order (`order_arrived`), never both — both
  foreign keys are nullable and independent rather than a single polymorphic
  reference.
- Every table also carries `created_at`/`updated_at` (omitted above for
  readability) via the shared `TimestampMixin` — see
  `backend/app/models/base.py`.
- All four enums (`role`, `status`, `type`, `severity`) are native Postgres
  `ENUM` types, not free-text columns — see `schema.sql` for their exact
  values.
