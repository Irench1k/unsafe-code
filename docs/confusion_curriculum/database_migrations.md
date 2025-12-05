# Database Schema Changes (r01–r03)

This document captures only the moments when the data model actually changes. When a release introduces new routes or guards but the persisted structures stay the same, it is omitted on purpose.

## r01 – Input Source Confusion

| Version | Schema change |
| --- | --- |
| v101 (`r01/e01_dual_parameter`) | Baseline in-memory store with three collections: `menu_items`, `users`, and `orders`. `Order` holds only `order_id`, `user_id`, `items`, `total`, and timestamps. |
| v102 (`r01/e02_delivery_fee`) | `Order` snapshots now persist delivery metadata. Two new fields are stored for every order: `delivery_fee` and `delivery_address`. |
| v103 (`r01/e03_order_overwrite`) | Cart-based checkout introduces a new `carts` collection plus `next_cart_id`. Each cart stores `cart_id` and an array of menu item IDs. |
| v104 (`r01/e04_negative_tip`) | `orders` gain a `tip` field so gratuity is written alongside delivery info. |
| v105 (`r01/e05_unlimited_refund`) | Refund tracking is added. A dedicated `refunds` collection maintains `refund_id`, `order_id`, `amount`, `status`, `auto_approved`, and timestamps. |
| v106–v107 | Email verification logic changes request processing only. No new tables or columns land after refunds. |

## r02 – Authentication Confusion

| Version | Schema change |
| --- | --- |
| v201 (`r02/e01_session_hijack`) | User records switch to email-based identifiers. `User.user_id` now stores the email address, and `Cart` gains an `owner_id` (email) so carts can be tied to either cookie or Basic Auth flows. Seed data and lookups across `database/storage.py` and `database/repository.py` are rewritten accordingly. |
| v203 (`r02/e03_fake_header_refund`) | Refunds now record payout state. A `paid` boolean is appended to each refund record so the manager workflow can differentiate pending approvals from money that actually left the platform. |
| v204–v205 | Auth refactors do not touch persistence; the repositories, models, and fixtures stay identical to v203. |

## r03 – Authorization Confusion

| Version | Schema change |
| --- | --- |
| v301 (`r03/e01_dual_auth_refund`) | Full migration from the in-memory dictionaries to PostgreSQL/SQLAlchemy. New normalized tables cover `restaurants`, `users`, `menu_items`, `orders`, `order_items`, `carts`, `cart_items`, `refunds`, and `platform_config`. Each model now specifies explicit numeric IDs, foreign keys, enums, and numeric column constraints. |
| v302–v305 | Authorization helpers, stored procedures, and decorators evolve, but the ORM models remain untouched through these releases. |
| v306 (`r03/e06_domain_token_any_mailbox`) | Restaurant self-registration now persists each tenant’s claimed domain. The `restaurants` table gains a required `domain` column that stores the canonical email domain used for API-key issuance and future role assignment. |
| v307 (`r03/e07_token_swap_hijack`) | Middleware keeps mutating request context only—the schema introduced in v306 remains unchanged. |
