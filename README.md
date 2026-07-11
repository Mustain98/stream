# Stream — Pay-Per-View Live Streaming Platform

**Stream** is a full-stack live-streaming platform where creators broadcast in real time over WebRTC and get paid for it. Viewers can watch free streams instantly, sample paid streams through timed free previews, and unlock full access with a Stripe checkout — while broadcasters watch their earnings update live and receive automatic payouts to their own Stripe account when the stream ends.

Unlike platforms built on off-the-shelf media servers, Stream runs on a **custom Python SFU (Selective Forwarding Unit)** built from scratch with `aiortc` — the media routing, room management, signaling, preview enforcement, and moderation logic are all first-party code.

---

## ✨ What It Does

### 🎥 Real-Time Broadcasting (Custom WebRTC SFU)
- One-to-many live video/audio powered by a hand-rolled SFU — a single publisher's tracks are selectively forwarded to any number of subscribers.
- WebSocket signaling handles the full WebRTC lifecycle: offer/answer negotiation, ICE candidate exchange, and clean peer teardown.
- Broadcasters can **pause and resume** their stream mid-broadcast; viewers see the state change instantly.
- A **publisher heartbeat** keeps the backend informed that a stream is genuinely live; a background cleanup loop reaps streams whose broadcaster disappeared.

### 🔐 Ticket-Based Stream Access
Viewers never connect to the media server with raw credentials. Instead:
1. The main backend authenticates the user (JWT) and verifies their right to watch (free stream, valid payment, or preview eligibility).
2. It issues a **short-lived, single-purpose SFU ticket**.
3. The SFU validates the ticket against the backend over a shared-secret internal API before admitting the peer.

This cleanly separates the *business* layer (who may watch) from the *media* layer (packet forwarding).

### 💳 Monetization with Stripe
- Broadcasters mark a stream **free or paid**, set the price, currency, and an optional **free preview window** (e.g. "first 60 seconds free").
- Paid access goes through **Stripe Checkout**, confirmed by webhooks with a reconciliation endpoint as a safety net for missed events.
- Payments are idempotent and duplicate-proof: a partial unique index guarantees at most one paid transaction per viewer per stream, and every Stripe call carries an idempotency key.
- A configurable **platform fee** (default 10%) is split out of every transaction.

### 🕒 Free Previews That Actually End
The preview isn't a client-side timer someone can bypass — the **SFU itself enforces it**. When a preview viewer's time is up, the media server cuts the connection and the frontend swaps in a payment-required overlay leading straight to checkout.

### 💰 Settlement, Payouts & Viewer Protection
- Broadcasters onboard to **Stripe Connect** directly from their dashboard.
- When a stream ends, a settlement pass runs automatically:
  - **Stream met its minimum duration?** → Each paid viewer's share (minus platform fee) is transferred to the broadcaster's connected account.
  - **Stream ended too early?** → Viewers are **automatically refunded**. No support tickets, no manual intervention.
- Late payments (e.g. a webhook that lands after the stream ended) are settled individually with the same rules.
- Full transaction state machine: `pending → checkout_created → paid → transferred / refunded`, with failure states tracked at every step.

### 📊 Live Earnings & Analytics
- Broadcasters see a **real-time earnings panel in the studio** — every confirmed payment is relayed from the backend through the SFU to the broadcaster over the existing WebSocket, mid-stream.
- The dashboard includes an **earnings bar chart**, plus full **earnings history** (as a creator) and **spend history** (as a viewer).

### 💬 Live Chat with Mentions
- Chat rides on the same signaling WebSocket — no extra infrastructure.
- `@username` mentions trigger **targeted notifications** to the mentioned viewer.

### 🛡️ Moderation
- Broadcasters can **block, unblock, and kick** viewers from the studio.
- Blocks are enforced at both layers: the SFU ejects the user from the room immediately, and the backend refuses to issue them a new ticket.
- A blocked-users panel shows and manages the block list per stream.

### 👤 Accounts & Discovery
- JWT-based signup/login with Argon2/bcrypt password hashing.
- Editable user profile, personal dashboard, browse pages for **live**, **upcoming (scheduled)**, and **owned** streams.
- Streams support scheduling (planned start/end times) and full event auditing (start, end, join, leave, block, unblock).

---

## 🏗️ Architecture

Three services, one database:

```
                    ┌──────────────────────┐
                    │       Frontend       │
                    │  Next.js 15 / React  │
                    └─────┬──────────┬─────┘
             REST (JWT)   │          │   WebRTC + WebSocket
                          ▼          ▼      (ticket auth)
        ┌─────────────────────┐   ┌──────────────────────┐
        │    Main Backend     │◄──┤   Stream Server      │
        │      FastAPI        │   │  Custom Python SFU   │
        │                     ├──►│      (aiortc)        │
        │ auth · streams ·    │   │                      │
        │ payments · earnings │   │ rooms · media router │
        │ moderation · connect│   │ signaling · previews │
        └──────┬───────┬──────┘   └──────────────────────┘
               │       │            internal API secured
               ▼       ▼            by shared secret
        ┌──────────┐ ┌────────┐
        │ Postgres │ │ Stripe │
        └──────────┘ └────────┘
```

| Service | Directory | Stack | Responsibility |
|---|---|---|---|
| **Frontend** | [frontend/](frontend/) | Next.js 15, React 19, TypeScript | Studio, watch page, dashboard, checkout flows |
| **Main Backend** | [backend/](backend/) | FastAPI, SQLModel, PostgreSQL, Stripe | Auth, stream metadata, tickets, payments, settlement, earnings, moderation |
| **Stream Server** | [stream_server/](stream_server/) | FastAPI, aiortc, WebSockets | WebRTC media forwarding, signaling, chat, preview enforcement, room state |

The backend is organized as **feature modules** (`auth`, `stream`, `viewer`, `payment`, `earnings`, `connect`, `moderation`, `preview`), each with its own routers → controllers → services → models layering. The two servers talk to each other over authenticated internal endpoints: the backend pushes kicks, unblocks, and earnings updates into live rooms; the SFU validates tickets and reports stream lifecycle events back.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+, Node.js 18+, Docker

### 1. Database
```bash
docker compose up -d          # Postgres 16 on localhost:55432
```

### 2. Main Backend (port 8000)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Stream Server / SFU (port 8001)
```bash
cd stream_server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 4. Frontend (port 3000)
```bash
cd frontend
npm install
npm run dev
```

### 5. Stripe webhooks (for paid streams)
```bash
docker compose -f docker-compose.stripe.yml up -d
# forwards Stripe events to http://localhost:8000/payments/stripe/webhook
```

### Environment Variables

**Backend** (`backend/.env`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT auth |
| `FRONTEND_ORIGIN` | CORS allowlist |
| `SFU_HTTP_URL`, `SFU_WS_URL` | Stream server endpoints |
| `SFU_INTERNAL_SECRET` | Shared secret for backend ↔ SFU internal API |
| `SFU_TICKET_EXPIRE_SECONDS` | Ticket lifetime |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Stripe integration |
| `PLATFORM_FEE_PERCENT` | Platform's cut of paid streams (default 10) |
| `LIVE_TTL_SECONDS`, `SFU_HEARTBEAT_INTERVAL_SECONDS`, `STREAM_CLEANUP_INTERVAL_SECONDS` | Liveness / cleanup tuning |

**Stream server** (`stream_server/.env`): `MAIN_BACKEND_URL`, `SFU_INTERNAL_SECRET`, `FRONTEND_ORIGIN`

**Frontend** (`frontend/.env.local`): `NEXT_PUBLIC_API_BASE_URL`

---

## 🔌 API Surface (Highlights)

| Area | Endpoints |
|---|---|
| Auth | `POST /signup`, `POST /login`, `GET/PATCH /me`, `GET /dashboard` |
| Streams | `POST /create`, `POST /start/{id}`, `POST /end/{id}`, `GET /live`, `GET /upcoming`, `GET /owned` |
| Access | `POST /ticket/{id}` (SFU ticket), `GET /{id}/access`, `PATCH /{id}/access-settings` |
| Payments | `POST /stream/{id}/checkout`, `POST /payments/stripe/webhook`, `POST /payments/stripe/reconcile-checkout` |
| Earnings | `GET /{id}/earnings`, `GET /earnings/history`, `GET /spend/history` |
| Moderation | `POST/DELETE /{id}/block/{user_id}`, `GET /{id}/blocked-users` |
| Connect | `POST /onboard`, `GET /status` (Stripe Connect) |
| SFU | `WS /ws` (signaling + chat), `GET /rooms` (room inspector) |

---

## 💡 Why This Project Is Interesting

- **The hard part is hand-built.** Most streaming demos wrap Mediasoup, LiveKit, or Agora. Here the SFU — peer management, track forwarding, room lifecycle, preview timers — is original `aiortc` code you can read end to end.
- **Money is handled like production money.** Idempotency keys, webhook replay protection, DB-level uniqueness of paid access, a reconciliation escape hatch, split fees, automated Connect payouts, and automatic refunds when a broadcaster under-delivers.
- **Real-time everywhere.** Video, chat, mentions, moderation actions, and earnings updates all propagate live over a single WebSocket per viewer.
- **Clean separation of concerns.** The media server knows nothing about passwords or payments; the business backend never touches an RTP packet. A short-lived ticket is the only bridge.
