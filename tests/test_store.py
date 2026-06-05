"""Durable snapshot store: write-through to the DB mirror on set, and cold
reload from it when the in-memory copy is empty (the server-restart /
serverless cold-start path that v28 onward relies on)."""
import time

from store import Snapshot, Store


def test_get_serves_in_memory_after_set(fresh_db):
    st = Store()
    st.set(Snapshot(received_at=time.time(), ts="t", node_id=7,
                    node_wallet="0x" + "a" * 40, model_short="Warm.gguf",
                    rounds_participated_today=3))
    got = st.get(7)
    assert got is not None
    assert got.model_short == "Warm.gguf"
    assert got.rounds_participated_today == 3


def test_cold_get_rehydrates_from_db(fresh_db):
    # Write with one Store, read with a fresh Store (empty in-memory) -> it must
    # reload from the durable mirror, exactly like a cold serverless invocation.
    Store().set(Snapshot(received_at=time.time(), ts="t", node_id=9,
                         node_wallet="0x" + "b" * 40, model_short="Cold.gguf",
                         rounds_participated_today=5,
                         recent_rounds=[{"hash": "abc", "tx_hash": "0xT"}]))
    cold = Store()
    got = cold.get(9)
    assert got is not None
    assert got.model_short == "Cold.gguf"
    assert got.rounds_participated_today == 5
    assert got.node_wallet == "0x" + "b" * 40
    assert got.recent_rounds == [{"hash": "abc", "tx_hash": "0xT"}]


def test_known_node_ids_includes_persisted(fresh_db):
    # Distinct Store instances share the durable mirror -> known ids come from
    # the DB even when this instance never saw the push in memory.
    Store().set(Snapshot(received_at=time.time(), node_id=2))
    Store().set(Snapshot(received_at=time.time(), node_id=5))
    assert Store().known_node_ids() == [2, 5]


def test_set_latest_wins(fresh_db):
    st = Store()
    st.set(Snapshot(received_at=1.0, node_id=1, model_short="old"))
    st.set(Snapshot(received_at=2.0, node_id=1, model_short="new"))
    assert Store().get(1).model_short == "new"   # fresh Store reads the mirror
