"""
Run:  python3 -m pytest tests/ -q      (or: python3 tests/test_psi.py)
All tests are offline: network calls are replaced with fakes.
"""
import json, os, sys, datetime as dt, tempfile, shutil, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import psi_engine as E

FROZEN = os.path.join(ROOT, "tests", "fixtures", "frozen_raw.json")   # the 2,150-record snapshot of 2026-08-15
GOLDEN = os.path.join(ROOT, "tests", "fixtures", "metrics_golden.json")
AS_OF = dt.date(2026, 8, 15)

def load_frozen():
    return json.load(open(FROZEN))

# ---------------- unit tests: the statistics ----------------
def test_quantile_matches_numpy_linear():
    s = [1, 2, 3, 4]
    assert E.quantile(s, 0) == 1 and E.quantile(s, 1) == 4
    assert abs(E.quantile(s, 0.5) - 2.5) < 1e-9
    assert abs(E.quantile(s, 0.25) - 1.75) < 1e-9

def test_pct_rank_midrank_on_ties():
    s = [7.0, 7.5, 7.5, 8.0]
    assert abs(E.pct_rank(s, 7.5) - 50.0) < 1e-9        # 1 below + half of 2 equal = 2 of 4
    assert abs(E.pct_rank(s, 9.0) - 100.0) < 1e-9
    assert abs(E.pct_rank(s, 6.0) - 0.0) < 1e-9

def test_grades_thresholds():
    assert E.grade_for(99) == "Rarefied air" and E.grade_for(97) == "Rarefied air"
    assert E.grade_for(90) == "Elite" and E.grade_for(89.9) == "Great"
    assert E.grade_for(0) == "Bad"

# ---------------- golden test: the whole engine on the frozen archive ----------------
def test_golden_metrics_unchanged():
    rows = E.normalize(load_frozen()); m = E.compute(rows, as_of=AS_OF)
    g = json.load(open(GOLDEN))
    assert m["counts"]["archive"] == 2150 and m["counts"]["calibration"] == 2121
    assert m["year_stats"] == g["year_stats"], "year table changed — if intentional, regenerate the golden and bump methodology_version"
    assert m["regime"] == g["regime"]
    for k in ("date", "score", "venue", "pct_now", "grade", "equiv_base_year", "higher_in_window"):
        assert m["latest"][k] == g["latest"][k]
    assert m["grid"] == g["grid"]

def test_hand_check_values_from_spec():
    rows = E.normalize(load_frozen()); m = E.compute(rows, as_of=AS_OF)
    assert m["latest"]["score"] == 8.2 and m["latest"]["higher_in_window"] == 2 and round(m["latest"]["pct_now"]) == 95
    ys = m["year_stats"]
    assert ys["2017"]["mean"] == 6.48 or abs(ys["2017"]["mean"] - 6.48) < 0.006
    assert abs(ys["2019"]["mean"] - 6.78) < 0.006 and abs(ys["2024"]["mean"] - 7.46) < 0.006
    assert m["nines"]["last"]["venue"] == "Ceres" and m["nines"]["reviews_since"] == 205

# ---------------- simulations of the poller (offline) ----------------
def _fresh_poller(tmpdir, state_records):
    os.environ["PSI_STATE"] = os.path.join(tmpdir, "ledger_raw.json"); os.environ["PSI_OUT"] = tmpdir
    json.dump(state_records, open(os.environ["PSI_STATE"], "w"))
    if "psi_poller" in sys.modules: del sys.modules["psi_poller"]
    return importlib.import_module("psi_poller")

def test_new_score_detected_and_verdict_written():
    raw = load_frozen(); newest = raw[0]; tmp = tempfile.mkdtemp()
    try:
        P = _fresh_poller(tmp, [r for r in raw if r["id"] != newest["id"]])
        P.fetch_newest = lambda n=25: raw[:n]; P.WEBHOOK = None
        sys.argv = ["psi_poller.py"]; P.main()
        st = json.load(open(os.path.join(tmp, "status.json"))); m = json.load(open(os.path.join(tmp, "metrics.json")))
        assert st["ok"] and st["changed"] == 1 and st["archive_count"] == 2150
        assert m["latest"]["venue"] == "Liguria Pizzeria" and m["latest"]["grade"] == "Elite"
    finally: shutil.rmtree(tmp)

def test_score_edit_detected_by_full_reconcile():
    raw = load_frozen(); tmp = tempfile.mkdtemp()
    try:
        edited = json.loads(json.dumps(raw)); edited[5]["score"] = round(edited[5]["score"] + 0.3, 1)
        P = _fresh_poller(tmp, raw); P.fetch_all = lambda: edited; P.WEBHOOK = None
        sys.argv = ["psi_poller.py", "--full"]; P.main()
        st = json.load(open(os.path.join(tmp, "status.json")))
        assert st["ok"] and "1 edits" in st["message"]
        assert os.path.exists(os.path.join(tmp, "changelog.jsonl"))
    finally: shutil.rmtree(tmp)

def test_api_down_falls_back_to_html():
    raw = load_frozen(); tmp = tempfile.mkdtemp()
    try:
        P = _fresh_poller(tmp, raw)
        def boom(limit=100, offset=0): raise RuntimeError("HTTP 503")
        P.fetch_api = boom; P.fetch_html_fallback = lambda page=1: raw[:30]; P.WEBHOOK = None
        sys.argv = ["psi_poller.py"]; P.main()
        st = json.load(open(os.path.join(tmp, "status.json")))
        assert st["ok"] and st["source"] == "html_fallback"
    finally: shutil.rmtree(tmp)

def test_schema_drift_blocks_writes():
    raw = load_frozen(); tmp = tempfile.mkdtemp()
    try:
        P = _fresh_poller(tmp, raw)
        broken = [dict(r) for r in raw[:25]]; del broken[0]["score"]
        P.fetch_api = lambda limit=100, offset=0: P.validate(broken); P.WEBHOOK = None
        sys.argv = ["psi_poller.py"]
        try: P.main(); assert False, "expected SystemExit(2)"
        except SystemExit as e: assert e.code == 2
        st = json.load(open(os.path.join(tmp, "status.json")))
        assert st["ok"] is False and "SCHEMA DRIFT" in st["message"]
        assert not os.path.exists(os.path.join(tmp, "metrics.json"))     # nothing written
    finally: shutil.rmtree(tmp)

def test_staleness_signal_available():
    rows = E.normalize(load_frozen()); m = E.compute(rows, as_of=AS_OF)
    last = dt.date.fromisoformat(m["counts"]["last_date"])
    assert (AS_OF - last).days <= 10   # the alert rule: newest record older than 10 days => alert

if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fails = 0
    for t in tests:
        try: t(); print("PASS", t.__name__)
        except Exception: fails += 1; print("FAIL", t.__name__); traceback.print_exc()
    print(f"\n{len(tests)-fails}/{len(tests)} passed"); sys.exit(1 if fails else 0)
