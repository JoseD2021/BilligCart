"""Durable technical ledger + transactional outbox, independent of Supabase.

Single-host SQLite adapter. API and workers share the same mounted directory.
All state changes and outbox inserts commit in the same transaction.
"""
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from uuid import uuid4

from src.domain.entities.payment import Payment, PaymentQuote, PaymentStatus
from src.domain.errors import InvalidRequestBodyError
from src.events.contracts.event_envelope import EventEnvelope
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded

logger = logging.getLogger(__name__)


class PaymentStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY, user_id TEXT, order_id TEXT, created REAL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS payment_order ON payments(user_id, order_id, created);
                CREATE TABLE IF NOT EXISTS request_keys (
                    user_id TEXT, key TEXT, payment_id TEXT, PRIMARY KEY(user_id, key));
                CREATE TABLE IF NOT EXISTS outbox (
                    event_id TEXT PRIMARY KEY, body TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS webhook_inbox (event_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS projection_inbox (event_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS projection_receipts (
                    event_id TEXT, target TEXT, applied_at REAL NOT NULL,
                    PRIMARY KEY(event_id, target));
                CREATE TABLE IF NOT EXISTS paid_orders (
                    order_id TEXT PRIMARY KEY, payment_id TEXT NOT NULL, event TEXT NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _entity(row):
        if row is None:
            return None
        data = json.loads(row["data"])
        data["status"] = PaymentStatus(data["status"])
        return Payment(**data)

    @staticmethod
    def _write(db, payment):
        db.execute("INSERT OR REPLACE INTO payments VALUES(?,?,?,?,?)", (
            payment.id, payment.user_id, payment.order_id, payment.created_at,
            json.dumps(asdict(payment)),
        ))

    @staticmethod
    def _event(db, event):
        db.execute("INSERT OR IGNORE INTO outbox(event_id,body) VALUES(?,?)",
                   (event.event_id, EventEnvelope.from_event(event).to_json()))

    def get(self, payment_id):
        with self.transaction() as db:
            return self._entity(db.execute("SELECT data FROM payments WHERE id=?", (payment_id,)).fetchone())

    def current(self, user_id, order_id):
        with self.transaction() as db:
            return self._entity(db.execute(
                "SELECT data FROM payments WHERE user_id=? AND order_id=? ORDER BY created DESC LIMIT 1",
                (user_id, order_id)).fetchone())

    def by_key(self, user_id, key):
        with self.transaction() as db:
            return self._entity(db.execute(
                "SELECT p.data FROM payments p JOIN request_keys k ON p.id=k.payment_id WHERE k.user_id=? AND k.key=?",
                (user_id, key)).fetchone())

    def create(self, quote: PaymentQuote, key: str) -> Payment:
        created_event = None
        with self.transaction() as db:
            keyed = self._entity(db.execute(
                "SELECT p.data FROM payments p JOIN request_keys k ON p.id=k.payment_id WHERE k.user_id=? AND k.key=?",
                (quote.user_id, key)).fetchone())
            if keyed:
                if keyed.order_id != quote.order_id:
                    raise InvalidRequestBodyError("Idempotency-Key ya pertenece a otro pedido.")
                return keyed
            rows = db.execute("SELECT data FROM payments WHERE user_id=? AND order_id=? ORDER BY created DESC",
                              (quote.user_id, quote.order_id)).fetchall()
            # A paid order can never be charged again, even if a later attempt exists.
            existing = [self._entity(row) for row in rows]
            current = next((p for p in existing if p.status == PaymentStatus.SUCCEEDED), existing[0] if existing else None)
            if current and current.status not in (PaymentStatus.FAILED, PaymentStatus.EXPIRED):
                payment = current
            else:
                payment = Payment(str(uuid4()), quote.user_id, quote.order_id, quote.amount_minor,
                                  quote.currency.lower(), quote.version, quote.expires_at.timestamp(),
                                  PaymentStatus.QUEUED, time.time(), len(existing) + 1)
                self._write(db, payment)
                created_event = PaymentRequested(payment_id=payment.id)
                self._event(db, created_event)
            db.execute("INSERT INTO request_keys VALUES(?,?,?)", (quote.user_id, key, payment.id))
        if created_event:
            logger.info("payment_request_recorded payment_id=%s order_id=%s event_id=%s status=%s",
                        payment.id, payment.order_id, created_event.event_id, payment.status.value)
        return payment

    def update_queued(self, payment_id, **changes):
        with self.transaction() as db:
            payment = self._entity(db.execute("SELECT data FROM payments WHERE id=?", (payment_id,)).fetchone())
            if payment and payment.status == PaymentStatus.QUEUED:
                payment = replace(payment, **changes)
                self._write(db, payment)
            return payment

    def webhook(self, event_id, payment_id, session, status):
        success_event = None
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM webhook_inbox WHERE event_id=?", (event_id,)).fetchone():
                logger.info("stripe_webhook_duplicate stripe_event_id=%s payment_id=%s", event_id, payment_id)
                return
            payment = self._entity(db.execute("SELECT data FROM payments WHERE id=?", (payment_id,)).fetchone())
            if payment is None:
                raise ValueError("Unknown payment")
            if (session.get("client_reference_id") != payment.id or
                session.get("amount_total") != payment.amount_minor or
                session.get("currency") != payment.currency or
                session.get("mode") != "payment" or
                (payment.provider_session_id and session["id"] != payment.provider_session_id)):
                raise ValueError("Session does not match the authorized quote")
            # Success is monotonic. Delayed failures cannot undo a confirmed payment.
            if payment.status != PaymentStatus.SUCCEEDED and not (
                status == PaymentStatus.PROCESSING and payment.status in (PaymentStatus.FAILED, PaymentStatus.EXPIRED)
            ):
                payment = replace(payment, status=status, provider_session_id=session["id"], error=None)
                self._write(db, payment)
                if status == PaymentStatus.SUCCEEDED:
                    success_event = PaymentSucceeded(
                        payment_id=payment.id, order_id=payment.order_id, user_id=payment.user_id,
                        amount_minor=payment.amount_minor, currency=payment.currency,
                        provider_session_id=session["id"],
                    )
                    self._event(db, success_event)
            db.execute("INSERT INTO webhook_inbox VALUES(?)", (event_id,))
        logger.info("stripe_webhook_applied stripe_event_id=%s payment_id=%s status=%s",
                    event_id, payment_id, payment.status.value)
        if success_event:
            logger.info("payment_event_recorded event_type=%s event_id=%s payment_id=%s order_id=%s",
                        success_event.event_type, success_event.event_id, payment.id, payment.order_id)

    def pending_events(self):
        with self.transaction() as db:
            return [dict(row) for row in db.execute("SELECT event_id,body FROM outbox WHERE sent=0 LIMIT 100")]

    def mark_sent(self, event_id):
        with self.transaction() as db:
            db.execute("UPDATE outbox SET sent=1 WHERE event_id=?", (event_id,))

    def stored_success(self, event_id):
        with self.transaction() as db:
            row = db.execute("SELECT body FROM outbox WHERE event_id=?", (event_id,)).fetchone()
        if row is None:
            return None
        envelope = EventEnvelope.from_json(row[0])
        return envelope if envelope.event_type == PaymentSucceeded.EVENT_TYPE else None

    def record_projection_receipt(self, event_id, target):
        with self.transaction() as db:
            db.execute("INSERT OR IGNORE INTO projection_receipts VALUES(?,?,?)", (event_id, target, time.time()))

    def requeue_unprojected_successes(self, target):
        """Replay durable successes after adding a new destination or after a crash."""
        with self.transaction() as db:
            rows = db.execute('''
                SELECT o.event_id FROM outbox o
                WHERE json_extract(o.body, '$.event_type') = ?
                AND NOT EXISTS (SELECT 1 FROM projection_receipts p
                                WHERE p.event_id=o.event_id AND p.target=?)
            ''', (PaymentSucceeded.EVENT_TYPE, target)).fetchall()
            for row in rows:
                db.execute("UPDATE outbox SET sent=0 WHERE event_id=?", (row[0],))
        return len(rows)

    def apply_projection(self, event):
        """Executable local projection; replace via PaymentProjection when schema is ready."""
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM projection_inbox WHERE event_id=?", (event["event_id"],)).fetchone():
                return False
            inserted = db.execute("INSERT OR IGNORE INTO paid_orders VALUES(?,?,?)",
                                  (event["order_id"], event["payment_id"], json.dumps(event))).rowcount > 0
            db.execute("INSERT INTO projection_inbox VALUES(?)", (event["event_id"],))
        return inserted
