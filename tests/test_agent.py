"""Agent telemetry parsing: GPU power summing (multi-GPU + [N/A]) and the
round-hash <-> decided-hash regex agreement that drives participation tagging."""
import json

import push_agent as pa


class _R:
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out


def test_gpu_power_sums_across_gpus(monkeypatch):
    monkeypatch.setattr(pa.subprocess, "run", lambda *a, **k: _R(
        0,
        "RTX 4090, 12000, 24576, 320.5\n"
        "RTX 4090, 11000, 24576, 310.0\n"
        "RTX 4090, 0, 24576, [N/A]",   # unreadable power -> skipped
    ))
    g = pa.get_gpu_info()
    assert g["name"] == "RTX 4090"
    assert g["power_w"] == 630.5


def test_gpu_power_all_na_is_none(monkeypatch):
    monkeypatch.setattr(pa.subprocess, "run", lambda *a, **k: _R(0, "GPU, 1, 2, [N/A]"))
    assert pa.get_gpu_info()["power_w"] is None


def test_round_and_decided_hash_match():
    # Participation tagging relies on these two regexes capturing the IDENTICAL
    # hash token; if a Capsule version changes the format this test fails loud.
    h = "77a789cb200381abe9c25902a428e153850abc3100789f10a41492f29256c153"
    completed = f"UTC 2026-05-29 16:19:32 INFO Inference round {h} completed. Total time: 245s"
    decided = f"UTC 2026-05-29 16:15:27 INFO Capsule has decided to participate in inference request {h}"
    assert pa.ROUND_DETAIL_RE.search(completed).group(4) == h
    assert pa.DECIDED_HASH_RE.search(decided).group(1) == h


def test_resolve_capsule_log_prefers_logs_on_mac(tmp_path):
    # macOS/Linux installers write FortytwoCapsule.logs (plural) -- the bug that
    # nulled model/version on Mac because the agent only looked for .log.
    debug = tmp_path / "FortytwoNode" / "debug"
    debug.mkdir(parents=True)
    (debug / "FortytwoCapsule.logs").write_text("x")
    assert pa.resolve_capsule_log(tmp_path).name == "FortytwoCapsule.logs"


def test_resolve_capsule_log_prefers_log_when_both_exist(tmp_path):
    # Windows writes .log; if both somehow exist, .log wins (back-compat).
    debug = tmp_path / "FortytwoNode" / "debug"
    debug.mkdir(parents=True)
    (debug / "FortytwoCapsule.log").write_text("x")
    (debug / "FortytwoCapsule.logs").write_text("x")
    assert pa.resolve_capsule_log(tmp_path).name == "FortytwoCapsule.log"


def test_protocol_version_regex_matches_current_format():
    # Real line on a live node: "Fortytwo Protocol Node current version: 0.25.1".
    # The old regex was case-sensitive in Python and missed it on macOS/Linux.
    line = "UTC 2026-05-31 19:23:53 INFO Fortytwo Protocol Node current version: 0.25.1"
    m = pa.PROTOCOL_VERSION_RE.search(line)
    assert m and m.group(1) == "0.25.1"


# ---------- auto-discovery helpers ----------


def test_parse_operator_wallet_last_match_wins():
    # A node re-logs its wallet on every restart; the LAST line is the truth.
    text = (
        "UTC INFO Operator Wallet Address: 0x" + "a" * 40 + "\n"
        "noise\n"
        "UTC INFO Operator Wallet Address: 0x" + "b" * 40 + "\n"
    )
    assert pa.parse_operator_wallet(text) == "0x" + "b" * 40


def test_parse_operator_wallet_absent_returns_none():
    assert pa.parse_operator_wallet("no wallet logged here\n") is None
    assert pa.parse_operator_wallet("") is None


def test_scripts_root_from_capsule_exe_is_two_levels_up(tmp_path):
    # Windows layout: <scripts-root>\FortytwoNode\FortytwoCapsule.exe. Built from
    # tmp_path so the assertion is correct on whatever OS runs the tests.
    exe = tmp_path / "FortytwoNode" / "FortytwoCapsule.exe"
    assert pa.scripts_root_from_capsule_exe(str(exe)) == tmp_path


def test_resolve_ready_url_parses_port_from_capsule_log(tmp_path):
    # The log says 0.0.0.0 but we must always probe 127.0.0.1.
    log = tmp_path / "FortytwoCapsule.log"
    log.write_text(
        "INFO starting\nINFO Server running at http://0.0.0.0:42444\nINFO ready\n"
    )
    assert pa.resolve_ready_url(log) == "http://127.0.0.1:42444/ready"


def test_resolve_ready_url_falls_back_when_missing(tmp_path):
    assert pa.resolve_ready_url(tmp_path / "nope.log") == "http://127.0.0.1:42442/ready"


def test_assign_node_id_stable_lowercased_and_persistent(tmp_path):
    mp = tmp_path / "discovered-nodes.json"
    a = "0x" + "A" * 40  # uppercase
    b = "0x" + "c" * 40
    assert pa.assign_node_id(a, mp) == 1
    # Same wallet, different casing -> same id (no reshuffle).
    assert pa.assign_node_id(a.lower(), mp) == 1
    # New wallet -> next free int.
    assert pa.assign_node_id(b, mp) == 2
    # Survives a fresh load (ids persisted to disk).
    reloaded = pa.load_node_map(mp)
    assert reloaded[a.lower()] == 1
    assert reloaded[b.lower()] == 2


def test_assign_node_id_fills_lowest_unused(tmp_path):
    mp = tmp_path / "discovered-nodes.json"
    # Pre-seed an id-2 wallet; a brand-new wallet should take the gap at 1.
    pa.save_node_map({"0x" + "d" * 40: 2}, mp)
    assert pa.assign_node_id("0x" + "e" * 40, mp) == 1


def test_post_snapshot_sends_node_wallet_not_wallet(monkeypatch):
    # The server reads "node_wallet"; a bare "wallet" key is silently dropped.
    # Capture the POST body and assert the field name is correct.
    captured = {}

    class _Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=0):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setattr(pa.urllib.request, "urlopen", fake_urlopen)
    wallet = "0x" + "f" * 40
    pa.post_snapshot("http://x", "tok", {"rounds_participated_today": 0,
                                         "model_short": "m", "capsule_alive": True,
                                         "protocol_alive": True},
                     node_id=7, wallet=wallet)
    assert captured["body"]["node_wallet"] == wallet
    assert captured["body"]["node_id"] == 7
    assert "wallet" not in captured["body"]  # the old, ignored key is gone


def test_post_snapshot_omits_wallet_when_absent(monkeypatch):
    # No wallet -> omit the field entirely (an empty/invalid value would 422).
    captured = {}

    class _Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(pa.urllib.request, "urlopen",
                        lambda req, timeout=0: captured.update(
                            body=json.loads(req.data.decode("utf-8"))) or _Resp())
    pa.post_snapshot("http://x", "tok", {"rounds_participated_today": 0,
                                         "model_short": "m", "capsule_alive": False,
                                         "protocol_alive": False}, node_id=1)
    assert "node_wallet" not in captured["body"]
