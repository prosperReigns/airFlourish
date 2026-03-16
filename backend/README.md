# Travel Platform Backend API

A scalable backend system for a global travel platform that allows users to book **flights, hotels, transport, and visa services** while handling **secure payments, wallet accounting, transaction tracking, notifications, and audit logging**.

This project is designed using a **modular Django architecture** with asynchronous processing for reliability and scalability.

---

# Table of Contents

* [Project Overview](#project-overview)
* [Key Features](#key-features)
* [System Architecture](#system-architecture)
* [Technology Stack](#technology-stack)
* [Project Structure](#project-structure)
* [Application Modules](#application-modules)
* [Core System Flow](#core-system-flow)
* [Installation & Setup](#installation--setup)
* [Environment Variables](#environment-variables)
* [Running the Project](#running-the-project)
* [Background Workers](#background-workers)
* [Payment Integration](#payment-integration)
* [API Endpoints](#api-endpoints)
* [Admin Controls](#admin-controls)
* [Security Practices](#security-practices)
* [Scalability Design](#scalability-design)
* [Future Enhancements](#future-enhancements)

---

# Project Overview

This backend powers a **travel services platform** where users can independently access and pay for multiple travel services:

* Flight booking
* Hotel reservations
* Airport transportation
* Visa applications

The system is designed so that **each service works independently**, while all financial activity flows through a **unified transaction, wallet, and ledger system**.

Key design principles:

* Modular architecture
* Secure payment processing
* Async task handling
* Financial integrity
* Clear audit trail

---

# Key Features

## User Features

* Secure authentication
* Flight search and booking
* Hotel booking
* Transport booking
* Visa applications
* Wallet transaction history
* Notification system

## System Features

* Payment processing via Flutterwave
* Transaction management
* Wallet accounting
* Ledger entries for financial traceability
* Notification delivery
* Audit logging
* Background processing with Celery

---

# System Architecture

The platform follows a **transaction-driven architecture**.

User actions flow through a consistent pipeline:

```
User Action
   ↓
Booking Module
   ↓
Transaction Created
   ↓
Payment Initiated
   ↓
Payment Verification (Async Worker)
   ↓
Wallet Updated
   ↓
Ledger Entry Recorded
   ↓
Booking Confirmed
   ↓
Notification Sent
   ↓
Audit Log Recorded
```

This architecture ensures:

* Payment reliability
* Financial traceability
* Scalability
* Separation of concerns

---

# Technology Stack

## Backend Framework

* Python
* Django
* Django REST Framework

## Background Processing

* Celery
* Redis (message broker)

## Database

* PostgreSQL

## Payments

* Flutterwave API

## External Travel APIs

* Sabre (Flights)
* Hotel provider APIs

## Authentication

* JWT Authentication

---

# Project Structure

```
backend/
│
├── app/
│   ├── users/
│   ├── flights/
│   ├── hotels/
│   ├── transport/
│   ├── visa/
│   ├── payments/
│   ├── transactions/
│   ├── wallets/
│   ├── ledger/
│   ├── notifications/
│   └── audit/
│
├── config/
│   ├── settings/
│   ├── urls.py
│   └── celery.py
│
├── manage.py
└── requirements.txt
```

Each module is responsible for a specific domain.

---

# Application Modules

## Users

Handles:

* authentication
* user profiles
* JWT token management

---

## Flights

Handles:

* flight search
* flight booking
* passenger data
* integration with Sabre API

---

## Hotels

Handles:

* hotel search
* hotel reservations
* booking confirmations

---

## Transport

Handles:

* airport transfers
* local travel services
* transport booking

---

## Visa

Handles:

* visa application submissions
* visa processing requests

---

## Payments

Handles:

* Flutterwave integration
* payment initialization
* payment verification
* webhook processing

---

## Transactions

Central financial record system.

Tracks:

* payment reference
* transaction status
* payment type
* user relationship

### Transaction Status

* `pending`
* `success`
* `failed`

---

## Wallets

Each user has a wallet used to track financial activity.

Responsibilities:

* track balances
* record wallet updates

---

## Ledger

Provides a **double-entry financial record**.

Every wallet change creates a ledger entry.

Ensures:

* financial transparency
* audit compliance

---

## Notifications

Handles user notifications such as:

* booking confirmations
* payment success
* payment failure
* system alerts

Users can:

* view notifications
* mark notifications as read

---

## Audit Logs

Records system activities for security and monitoring.

Examples:

* booking created
* payment verified
* wallet updated

---

# Core System Flow

### Example: Flight Booking

1. User logs in.
2. User searches flights.
3. User selects flight.
4. Booking record created.
5. Transaction created.
6. Payment initiated via Flutterwave.
7. Flutterwave sends webhook.
8. Celery worker verifies payment.
9. Wallet updated.
10. Ledger entry created.
11. Flight ticket issued.
12. Notification sent.
13. Audit log recorded.

---

# Installation & Setup

### Clone the repository

```bash
git clone <repository-url>
cd backend
```

### Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file.

Example:

```
SECRET_KEY=your_secret_key
DEBUG=True

DATABASE_URL=postgresql://user:password@localhost:5432/travel_db

FLUTTERWAVE_PUBLIC_KEY=your_public_key
FLUTTERWAVE_SECRET_KEY=your_secret_key

REDIS_URL=redis://localhost:6379
```

---

# Running the Project

### Apply migrations

```bash
python manage.py migrate
```

### Create admin user

```bash
python manage.py createsuperuser
```

### Start development server

```bash
python manage.py runserver
```

---

# Background Workers

Celery handles long running tasks.

### Start Redis

```bash
redis-server
```

### Start Celery worker

```bash
celery -A config worker -l info
```

### Start Celery beat (optional)

```bash
celery -A config beat -l info
```

---

# Payment Integration

Payments are processed using **Flutterwave**.

Payment flow:

1. Transaction created
2. Payment initialized
3. User completes payment
4. Flutterwave sends webhook
5. System verifies payment
6. Transaction status updated

Important:

The system **never stores card data**.

---

# Example API Endpoints

## Authentication

```
POST /api/auth/login
POST /api/auth/register
```

## Flights

```
GET /api/flights/search
POST /api/flights/book
```

## Hotels

```
GET /api/hotels/search
POST /api/hotels/book
```

## Transport

```
POST /api/transport/book
```

## Visa

```
POST /api/visa/apply
```

## Transactions

```
GET /api/transactions/
```

## Notifications

```
GET /api/notifications/
POST /api/notifications/read/
```

---

# Admin Controls

Administrators can view and manage:

* users
* bookings
* transactions
* wallets
* ledger entries
* notifications
* audit logs

Admin panel:

```
/admin
```

---

# Security Practices

The system implements:

* JWT authentication
* webhook verification
* idempotent transaction handling
* secure payment processing
* input validation
* role-based access control

Sensitive data is never stored in plaintext.

---

# Scalability Design

The architecture supports scaling by:

* asynchronous processing
* modular app design
* external service integrations
* stateless API endpoints

Future scaling may include:

* service separation
* containerization
* load balancing
* caching layers

---

# Future Enhancements

Potential improvements include:

* multi-currency support
* dynamic exchange rate conversion
* OAuth integration
* push notifications
* mobile SDK integration
* analytics dashboards
* fraud detection

---

# License

This project is intended for internal development and deployment by the travel services platform.
