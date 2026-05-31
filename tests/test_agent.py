"""Agent telemetry parsing: GPU power summing (multi-GPU + [N/A]) and the
round-hash <-> decided-hash regex agreement that drives participation tagging."""
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
