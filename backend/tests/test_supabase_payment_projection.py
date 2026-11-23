import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from test_payments import ORDER, USER, Quotes, stripe_event

from src.application.use_cases.payments import Payments
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.stripe_gateway import receive_webhook
from src.infrastructure.payments.supabase_projection import SupabasePaymentProjection
from src.infrastructure.payments.worker import SUCCESSES, PaymentWorker


class Database:
    def __init__(self):
        self.rows = {}
        self.calls = []
        self.fail_before_write = False
        self.fail_after_write = False

    def table(self, name):
        if name != "Pagos":
            raise AssertionError("Projection must not alter Pedidos or delivery state")
        return Query(self)


class Query:
    def __init__(self, database):
        self.database = database
        self.payload = None
        self.payment_id = None

    def upsert(self, payload, *, on_conflict, ignore_duplicates):
        assert on_conflict == "payment_id" and ignore_duplicates is True
        self.payload = payload
        return self

    def select(self, columns):
        return self

    def eq(self, column, value):
        assert column == "payment_id"
        self.payment_id = value
        return self

    async def execute(self):
        db = self.database
        if self.payload is None:
            row = db.rows.get(self.payment_id)
            return SimpleNamespace(data=[row] if row else [])
        if db.fail_before_write:
            raise ConnectionError("Supabase unavailable")
        db.calls.append(dict(self.payload))
        key = self.payload["payment_id"]
        inserted = key not in db.rows
        if inserted:
            db.rows[key] = self.payload | {"created_at": datetime.now(UTC).isoformat()}
        if db.fail_after_write:
            db.fail_after_write = False
            raise TimeoutError("Response lost after commit")
        return SimpleNamespace(data=[db.rows[key]] if inserted else [])


class ProjectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "journal.sqlite3")
        self.store = PaymentStore(self.path)
        self.payment = await Payments(self.store, Quotes()).request(USER, ORDER, "projection-key")
        receive_webhook(self.store, stripe_event(self.payment))
        row = next(row for row in self.store.pending_events() if "payments.succeeded.v1" in row["body"])
        self.body = row["body"]
        envelope = json.loads(self.body)
        self.event = envelope["payload"] | {"event_id": envelope["event_id"], "occurred_at": envelope["occurred_at"]}
        self.database = Database()
        self.projection = SupabasePaymentProjection(self.store, self.database)

    async def test_success_is_written_to_pagos_with_order_and_original_confirmation(self):
        await self.projection.apply(self.event)
        row = self.database.rows[self.payment.id]
        self.assertEqual(row["order_id"], ORDER)
        self.assertEqual(row["user_id"], USER)
        self.assertEqual(row["amount_minor"], 1000)
        self.assertEqual(row["status"], "succeeded")
        self.assertIs(row["livemode"], False)
        self.assertEqual(row["confirmed_at"], self.event["occurred_at"])

    async def test_repeated_delivery_keeps_one_row_and_records_target_receipt(self):
        await self.projection.apply(self.event)
        await self.projection.apply(self.event)
        self.assertEqual(len(self.database.rows), 1)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM projection_receipts WHERE target=?", (self.projection.target,)).fetchone()[0], 1)

    async def test_outage_does_not_record_a_successful_remote_receipt(self):
        self.database.fail_before_write = True
        with self.assertRaises(ConnectionError):
            await self.projection.apply(self.event)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM projection_receipts").fetchone()[0], 0)
        self.database.fail_before_write = False
        await self.projection.apply(self.event)
        self.assertEqual(len(self.database.rows), 1)

    async def test_lost_response_after_commit_can_retry_without_duplicate(self):
        self.database.fail_after_write = True
        with self.assertRaises(TimeoutError):
            await self.projection.apply(self.event)
        await self.projection.apply(self.event)
        self.assertEqual(len(self.database.rows), 1)

    async def test_altered_or_unknown_event_cannot_assert_a_paid_order(self):
        for event in (self.event | {"amount_minor": 1}, self.event | {"event_id": "unknown"}):
            with self.assertRaises(ValueError):
                await self.projection.apply(event)
        self.assertEqual(self.database.calls, [])

    async def test_conflicting_existing_row_is_not_overwritten(self):
        await self.projection.apply(self.event)
        self.database.rows[self.payment.id]["amount_minor"] = 1
        with self.assertRaises(ValueError):
            await self.projection.apply(self.event)
        self.assertEqual(self.database.rows[self.payment.id]["amount_minor"], 1)

    async def test_old_local_success_is_replayed_until_remote_commit(self):
        self.store.apply_projection(self.event)
        for row in self.store.pending_events():
            self.store.mark_sent(row["event_id"])
        self.assertEqual(self.store.requeue_unprojected_successes(self.projection.target), 1)
        self.assertEqual(len(self.store.pending_events()), 1)
        await self.projection.apply(self.event)
        restarted = PaymentStore(self.path)
        self.assertEqual(restarted.requeue_unprojected_successes(self.projection.target), 0)

    async def test_worker_delays_retry_when_supabase_is_down(self):
        self.database.fail_before_write = True
        worker = PaymentWorker(self.store, None, projection=self.projection)
        worker.channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=AsyncMock()))
        message = SimpleNamespace(body=self.body.encode(), headers={}, message_id=self.event["event_id"],
                                  ack=AsyncMock(), nack=AsyncMock())
        await worker.handle(message, SUCCESSES)
        message.ack.assert_awaited_once()
        self.assertEqual(worker.channel.default_exchange.publish.call_args.kwargs["routing_key"], SUCCESSES + ".retry.5")
        self.database.fail_before_write = False
        await worker.handle(message, SUCCESSES)
        self.assertEqual(len(self.database.rows), 1)
