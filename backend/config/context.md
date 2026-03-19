# BACKEND CONTEXT – TRAVEL PLATFORM

## IMPORTANT

This is a production-grade Django backend.

Do NOT generate random, generic, or simplified code.

All implementations must follow the architecture defined in this document.

---

# SYSTEM OVERVIEW

This is a modular Django backend powering a travel platform.

Users can independently:

* Book flights
* Book hotels
* Book transport
* Apply for visas

Each feature must work independently.

Users DO NOT need to book a flight before booking a hotel or any other service.

---

# CORE ARCHITECTURE FLOW

ALL business logic must follow this pipeline:

User Action
→ Booking Created
→ Transaction Created
→ Payment Initiated
→ Payment Verified (Async – Celery)
→ Wallet Updated
→ Ledger Entry Created
→ Booking Confirmed
→ Notification Sent
→ Audit Log Recorded

This flow is NOT optional.

---

# CURRENT SERVICE FLOWS

## Flights

1. Search flights  
   `GET /api/flights/search-flights/?origin=...&destination=...&departure_date=...&return_date=...`  
   * Calls Amadeus search  
   * Simplifies offers for UI  
   * Caches raw offers by `id` for secure booking

2. Secure book  
   `POST /api/flights/secure-book/`  
   Payload: `travelers` + `selected_flight_id` (or `flight_offer`)  
   * Creates `Booking` (service_type = flight)  
   * Creates `Payment` (pending) + `Transaction`  
   * Initiates Flutterwave hosted payment (card/bank transfer)

3. Payment verification  
   `POST /api/payments/webhook/flutterwave/`  
   * Verifies payment  
   * Celery `process_successful_payment` runs  
   * Amadeus flight order is created  
   * Booking + transaction are confirmed  
   * Notifications + audit logs are emitted

## Hotels

### A) Instant booking (pay now)
1. List hotels  
   `GET /api/hotels/`
2. Book secure  
   `POST /api/hotels/book-secure/`  
   * Creates `Booking` + `HotelReservation`  
   * Creates `Payment` (pending) + `Transaction`  
   * Initiates Flutterwave hosted payment
3. Webhook verification  
   * Confirms reservation + booking

### B) Reservation hold (pay later)
1. Create hold  
   `POST /api/hotels/hotel-reservation/`  
   Header: `Idempotency-Key`  
   * Creates `Booking` + `HotelReservation`  
   * Sets `hold_expires_at`

2. Checkout hold  
   `POST /api/hotels/checkout/`  
   Header: `Idempotency-Key`  
   * Creates `Payment` (pending) + `Transaction`  
   * Initiates Flutterwave hosted payment

3. Webhook verification  
   * Confirms reservation + booking

4. Hold expiry  
   * Celery beat runs `expire_hotel_reservation_holds` to cancel expired holds

---

## Visas

1. Discover visa types  
   `GET /api/visas/visa-types/?country=NG`  
   * Returns visa types with price, required documents, and processing days

2. Create application (draft)  
   `POST /api/visas/applications/`  
   Payload: `visa_type` (code, id, or name)

3. Upload documents  
   `POST /api/visas/applications/{id}/documents/`

4. Validate  
   `POST /api/visas/applications/{id}/validate/`  
   * Moves to `ready_for_payment` if complete

5. Checkout (payment)  
   `POST /api/visas/applications/{id}/checkout/`  
   Header: `Idempotency-Key`  
   * Creates `Booking` + `Payment` + `Transaction`  
   * Initiates Flutterwave hosted payment

6. Payment verification  
   `POST /api/payments/webhook/flutterwave/`  
   * Celery `process_successful_payment` sets visa status to `paid`

7. Submit  
   `POST /api/visas/applications/{id}/submit/`  
   * Locks application, status -> `submitted`

8. Admin review  
   `POST /api/visas/applications/{id}/review/`  
   `POST /api/visas/applications/{id}/approve/`  
   `POST /api/visas/applications/{id}/reject/`

---

# ARCHITECTURE RULES

## 1. Separation of Concerns

Follow strict layering:

* Models → Data only
* Views → Thin controllers
* Services → ALL business logic
* Tasks → Background processing
* Signals → Only for simple triggers

DO NOT:

* Put business logic inside views
* Call external APIs inside views
* Mix responsibilities

This follows standard Django architecture principles where layers are clearly separated for maintainability ([Medium][1]).

---

## 2. Modular App Design

Apps must remain independent:

* transactions
* wallets
* ledger
* payments
* notifications
* audit
* flights
* hotels
* transport
* visa

NO tight coupling between apps.

Communication must happen via:

* services
* events
* signals

---

## 3. Payments (CRITICAL)

We use Flutterwave.

Rules:

* NEVER store card details (cvv, card number, expiry)
* ALWAYS verify payments server-side
* ALWAYS use idempotency
* ALWAYS prevent duplicate transactions

Payment flow:

1. Create Transaction (status = pending)
2. Initialize payment
3. User pays
4. Webhook received
5. Celery verifies payment
6. Update transaction → success/failed

---

## 4. Transactions

Transactions are the SINGLE SOURCE OF TRUTH for money.

Rules:

* Every payment MUST have a transaction
* Transaction reference MUST be unique
* Transactions MUST be idempotent
* No duplicate processing allowed

---

## 5. Wallet + Ledger

Wallet:

* Stores user balance

Ledger:

* Immutable financial history

Rules:

* Every wallet update MUST create a ledger entry
* NEVER modify ledger entries
* Use atomic database transactions

---

## 6. Async Processing (Celery)

We use Celery + Redis.

Rules:

* ALL external API calls must be async
* Payment verification MUST be async
* Notifications MUST be async
* Retries must be implemented

Celery is used to offload long-running tasks and improve performance ([GeeksforGeeks][2]).

---

## 7. Notifications

Triggered after:

* payment success
* booking confirmation
* failures

Must support:

* unread/read state
* user-specific notifications

---

## 8. Audit Logs

Track ALL critical actions:

* booking created
* payment verified
* wallet updated

Audit logs must:

* include metadata
* be immutable
* be admin visible

---

## 9. Security Rules

* All endpoints must require authentication (except login/register)
* Use JWT
* Prevent:

  * SQL injection
  * XSS
  * invalid inputs

Django already provides strong built-in protections like ORM query safety and CSRF protection ([Medium][1]).

---

## 10. API DESIGN

* Use RESTful endpoints
* Proper HTTP status codes
* Consistent response format
* Pagination where needed

---

## 11. DO NOT BREAK THESE RULES

❌ Do NOT move business logic into views
❌ Do NOT skip transaction creation
❌ Do NOT update wallet without ledger
❌ Do NOT process payments synchronously
❌ Do NOT store sensitive payment data
❌ Do NOT tightly couple apps

---

# EXPECTED CODE PATTERNS

## GOOD

* services/payment_service.py
* services/booking_service.py
* tasks/payment_tasks.py
* models/transaction.py

## BAD

* views.py handling payment logic
* models doing external API calls
* random utility functions everywhere

---

# TESTING REQUIREMENTS

* Each app must have tests
* Cover:

  * success cases
  * failure cases
  * edge cases
  * concurrency
  * idempotency

---

# GOAL

This backend must behave like a production system similar to:

* financial systems
* booking platforms
* payment processors

It must be:

* scalable
* secure
* modular
* maintainable

---

# FINAL INSTRUCTION

When generating or modifying code:

1. Follow this architecture strictly
2. Do not simplify logic
3. Do not guess missing behavior — infer from system flow
4. Ensure consistency across all apps
5. Think like a senior backend engineer

If code violates these rules, refactor it.

[1]: https://medium.com/%40kunal.resolute/django-explained-end-to-end-architecture-orm-security-backend-design-2026-guide-71cb35adb0f8?utm_source=chatgpt.com "Django Explained End-to-End: Architecture, ORM, Security & Backend Design (2026 Guide) | by Kunal Kejriwal | Feb, 2026 | Medium"
[2]: https://www.geeksforgeeks.org/celery-integration-with-django/?utm_source=chatgpt.com "Celery Integration With Django - GeeksforGeeks"
