import asyncio
import json
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("oms_run", Path(__file__).with_name("run.py"))
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)


class _Alpha:
    def __init__(self, id):
        self.id = id


def test_namespace_prefixes_user_id():
    assert run.namespace("u1", "bqp_ml021") == "u1_bqp_ml021"


def test_prime_portfolio_payload_creates_only_the_portfolio():
    # Portfolio create carries no capital, exchange or oms_id -- those belong to
    # the account. Name mirrors the id so the per-owner name uniqueness Prime
    # enforces has the same collision space as the id.
    assert run.prime_portfolio_payload("u1_bqp_x") == {
        "name": "u1_bqp_x",
        "portfolioId": "u1_bqp_x",
    }


def test_prime_account_payload_sends_numeric_amount():
    p = run.prime_account_payload("u1_bqp_x", "u1_bqp_x", "bybit", "100000.00")
    assert p == {
        "portfolioId": "u1_bqp_x",
        "exchange": "bybit",
        "initialAmount": 100000.00,
        "omsId": "u1_bqp_x",
        "label": "u1_bqp_x · bybit",
    }
    # Prime's schema is z.number(); a string body field is a 400. The old
    # form-encoded endpoint coerced, the JSON one does not.
    assert isinstance(p["initialAmount"], float)


def test_prime_account_payload_label_distinguishes_venues():
    # The dashboard lists accounts by label, so two accounts of one strategy
    # have to be told apart by it -- the portfolio id alone is identical.
    a = run.prime_account_payload("u1_bqp_x", "oms_a", "bybit", 1)
    b = run.prime_account_payload("u1_bqp_x", "oms_b", "binance", 1)
    assert a["label"] != b["label"]
    assert "bybit" in a["label"] and "binance" in b["label"]


def test_prime_account_payload_omits_account_id():
    # Prime mints the account id itself and rejects a caller-supplied one.
    assert "accountId" not in run.prime_account_payload("p", "o", "binance", 1)


def test_exchange_slug_known_venues():
    from cybotrade.models import Exchange

    assert run.exchange_slug(Exchange.BYBIT_LINEAR) == "bybit"
    assert run.exchange_slug(Exchange.BINANCE_LINEAR) == "binance"


class _Resp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

    @property
    def is_success(self):
        return 200 <= self.status_code < 300


class _FakeClient:
    """Stands in for httpx.AsyncClient, replaying a queued list of responses and
    recording the calls made."""

    def __init__(self, responses, calls, raises=None):
        self._responses = responses
        self._calls = calls
        self._raises = raises

    def __call__(self, *_a, **_kw):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, url, headers=None, json=None):
        self._calls.append({"url": url, "headers": headers, "json": json})
        if self._raises:
            raise self._raises
        return self._responses.pop(0)


def _patch_httpx(monkeypatch, responses, calls, raises=None):
    import httpx

    monkeypatch.setattr(
        httpx, "AsyncClient", _FakeClient(responses, calls, raises), raising=True
    )


def _create(**kwargs):
    """prime_create is async and this project has no pytest-asyncio, so drive it
    with asyncio.run from a plain sync test."""
    defaults = {
        "prime_api": "https://p",
        "path": "/api/portfolio",
        "api_key": "k",
        "payload": {},
        "what": "thing",
    }
    defaults.update(kwargs)
    return asyncio.run(
        run.prime_create(
            defaults["prime_api"],
            defaults["path"],
            defaults["api_key"],
            defaults["payload"],
            what=defaults["what"],
            retry_missing=defaults.get("retry_missing", 0),
        )
    )


def test_prime_create_success(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, [_Resp(201)], calls)
    assert _create(payload={"name": "x"}, what="portfolio x") is True
    assert calls[0]["url"] == "https://p/api/portfolio"
    assert calls[0]["headers"]["x-api-key"] == "k"
    # JSON body, not multipart form.
    assert calls[0]["json"] == {"name": "x"}


def test_prime_create_treats_409_as_already_there(monkeypatch):
    # The whole point: creates re-run on every job start, so an existing
    # portfolio / oms_id must read as success, not failure.
    calls = []
    _patch_httpx(monkeypatch, [_Resp(409, "already exists")], calls)
    assert _create(path="/api/account", payload={"omsId": "o"}) is True


def test_prime_create_retries_404_then_succeeds(monkeypatch):
    # An oms-role pod can beat the portfolio-role pod to Prime; the portfolio
    # appears a moment later.
    calls = []
    _patch_httpx(monkeypatch, [_Resp(404), _Resp(404), _Resp(201)], calls)
    monkeypatch.setattr(run, "PRIME_ACCOUNT_RETRY_DELAY_S", 0)
    assert _create(path="/api/account", retry_missing=3) is True
    assert len(calls) == 3


def test_prime_create_gives_up_after_retries(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, [_Resp(404), _Resp(404)], calls)
    monkeypatch.setattr(run, "PRIME_ACCOUNT_RETRY_DELAY_S", 0)
    assert _create(path="/api/account", retry_missing=1) is False
    assert len(calls) == 2


def test_prime_create_no_retry_when_not_requested(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, [_Resp(404)], calls)
    assert _create(path="/api/account") is False
    assert len(calls) == 1


def test_prime_create_network_error_does_not_raise(monkeypatch):
    # Prime being unreachable must never stop paper trading.
    calls = []
    _patch_httpx(monkeypatch, [], calls, raises=RuntimeError("boom"))
    assert _create() is False


def test_prime_create_other_error_is_not_success(monkeypatch):
    calls = []
    _patch_httpx(monkeypatch, [_Resp(400, "bad body")], calls)
    assert _create() is False


def test_build_alpha_id_map_uses_original_ids_as_keys():
    alphas = [_Alpha("alpha_001"), _Alpha("alpha_002")]
    assert run.build_alpha_id_map("u1", alphas) == {
        "alpha_001": "u1_alpha_001",
        "alpha_002": "u1_alpha_002",
    }


def test_read_prime_api_key_reads_extra_key(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"oms_id": "x", "prime_api_key": "pk_123"}))
    assert run.read_prime_api_key(str(p)) == "pk_123"


def test_read_prime_api_key_missing_raises(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"oms_id": "x"}))
    with pytest.raises(ValueError):
        run.read_prime_api_key(str(p))


def test_nats_grpc_addr_default(monkeypatch):
    monkeypatch.delenv("BQ_AEGIS_NATS_GRPC_ADDR", raising=False)
    assert run.nats_grpc_addr("BQ_AEGIS_NATS_GRPC_ADDR", run.DEFAULT_AEGIS) == run.DEFAULT_AEGIS


def test_nats_grpc_addr_override(monkeypatch):
    monkeypatch.setenv("BQ_AEGIS_NATS_GRPC_ADDR", "host:50052")
    assert run.nats_grpc_addr("BQ_AEGIS_NATS_GRPC_ADDR", run.DEFAULT_AEGIS) == "host:50052"


def test_require_env_present(monkeypatch):
    monkeypatch.setenv("FOO_X", "v")
    assert run.require_env("FOO_X") == "v"


def test_require_env_missing_raises(monkeypatch):
    monkeypatch.delenv("FOO_X", raising=False)
    with pytest.raises(RuntimeError):
        run.require_env("FOO_X")


def test_read_prime_api_key_empty_raises(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"prime_api_key": ""}))
    with pytest.raises(ValueError):
        run.read_prime_api_key(str(p))


def test_load_setup_portfolio_from_py_path(tmp_path):
    mod = tmp_path / "p_mod.py"
    mod.write_text("async def setup_portfolio():\n    return 1, 2, 3, 4\n")
    fn = run.load_setup_portfolio(str(mod))
    assert callable(fn) and fn.__name__ == "setup_portfolio"
