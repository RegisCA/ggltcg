"""Token accounting on ``GeminiProvider``.

Every cost figure for this project was previously inferred from prompt structure
rather than measured, because nothing captured ``response.usage_metadata``. These
tests pin the accounting so a short calibration run can size a larger one.

The awkward cases are the ones that matter: an empty response still bills, and
the SDK's field names have drifted before, so a missing attribute must degrade to
zero rather than raise inside a live game.
"""

import threading
from types import SimpleNamespace

import pytest

from game_engine.ai.providers import (
    MODEL_PRICING_PER_MTOK,
    AIProviderConfig,
    GeminiProvider,
)


def _response(prompt=1000, output=100, thinking=0, cached=0, parts=True):
    part = SimpleNamespace(text='{"selected_index": 0}')
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=[part] if parts else []),
        finish_reason="STOP",
    )
    return SimpleNamespace(
        candidates=[candidate],
        text='{"selected_index": 0}',
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt,
            candidates_token_count=output,
            thoughts_token_count=thinking,
            cached_content_token_count=cached,
        ),
    )


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        return self._responses.pop(0)


def _provider(responses, model="gemini-2.5-flash-lite"):
    config = AIProviderConfig(api_key="k", model=model, fallback_model=model)
    return GeminiProvider(config, client=_FakeClient(responses))


@pytest.fixture(autouse=True)
def clean_usage():
    GeminiProvider.reset_usage()
    yield
    GeminiProvider.reset_usage()


def test_records_tokens_for_a_successful_call():
    provider = _provider([_response(prompt=1500, output=120)])
    provider.generate_json("p", {}, temperature=0.0, max_output_tokens=384)

    usage = GeminiProvider.get_usage()
    assert usage["requests"] == 1
    assert usage["prompt_tokens"] == 1500
    assert usage["output_tokens"] == 120


def test_accumulates_across_calls_and_splits_by_model():
    _provider([_response()], model="gemini-2.5-flash-lite").generate_json(
        "p", {}, temperature=0.0, max_output_tokens=384)
    _provider([_response()], model="gemini-2.0-flash").generate_json(
        "p", {}, temperature=0.0, max_output_tokens=384)

    usage = GeminiProvider.get_usage()
    assert usage["requests"] == 2
    assert set(usage["by_model"]) == {"gemini-2.5-flash-lite", "gemini-2.0-flash"}
    assert all(m["requests"] == 1 for m in usage["by_model"].values())


def test_an_empty_response_is_still_billed():
    """The expensive failure mode: output budget consumed, nothing returned, and
    the call is retried. If it were only recorded on success, a cost report would
    hide exactly the spend worth finding."""
    provider = _provider([_response(prompt=2000, output=0, parts=False)])
    with pytest.raises(Exception):
        provider.generate_json("p", {}, temperature=0.0, max_output_tokens=384,
                               retry_count=1, allow_fallback=False)

    usage = GeminiProvider.get_usage()
    assert usage["requests"] == 1
    assert usage["prompt_tokens"] == 2000


def test_missing_usage_metadata_does_not_raise():
    response = _response()
    del response.usage_metadata
    provider = _provider([response])

    provider.generate_json("p", {}, temperature=0.0, max_output_tokens=384)
    assert GeminiProvider.get_usage()["requests"] == 0


def test_unknown_field_names_degrade_to_zero():
    """SDK field names have changed before; a rename must cost data, not a crash."""
    response = _response()
    response.usage_metadata = SimpleNamespace(some_future_name=123)
    provider = _provider([response])

    provider.generate_json("p", {}, temperature=0.0, max_output_tokens=384)
    usage = GeminiProvider.get_usage()
    assert usage["requests"] == 1
    assert usage["prompt_tokens"] == 0


def test_cost_matches_the_published_rate():
    provider = _provider([_response(prompt=1_000_000, output=1_000_000)])
    provider.generate_json("p", {}, temperature=0.0, max_output_tokens=384)

    price_in, price_out = MODEL_PRICING_PER_MTOK["gemini-2.5-flash-lite"]
    assert GeminiProvider.get_usage()["est_cost_usd"] == pytest.approx(
        price_in + price_out, rel=1e-6)


def test_thinking_tokens_bill_as_output():
    """3.x models default to thinking on, and those tokens bill at the output
    rate. Omitting them would understate the cost of exactly the models the plan
    warns about."""
    provider = _provider([_response(prompt=0, output=0, thinking=1_000_000)])
    provider.generate_json("p", {}, temperature=0.0, max_output_tokens=384)

    _, price_out = MODEL_PRICING_PER_MTOK["gemini-2.5-flash-lite"]
    usage = GeminiProvider.get_usage()
    assert usage["thinking_tokens"] == 1_000_000
    assert usage["est_cost_usd"] == pytest.approx(price_out, rel=1e-6)


def test_concurrent_recording_loses_nothing():
    """Simulations fan out over a ThreadPoolExecutor; `+=` on a dict value is a
    read-modify-write and is not atomic under the GIL."""
    def worker():
        for _ in range(50):
            GeminiProvider._record_usage(_response(prompt=10, output=1),
                                         "gemini-2.5-flash-lite")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    usage = GeminiProvider.get_usage()
    assert usage["requests"] == 400
    assert usage["prompt_tokens"] == 4000
    assert usage["output_tokens"] == 400


def test_reset_clears_everything():
    _provider([_response()]).generate_json("p", {}, temperature=0.0, max_output_tokens=384)
    GeminiProvider.reset_usage()

    usage = GeminiProvider.get_usage()
    assert usage["requests"] == 0
    assert usage["by_model"] == {}
    assert usage["est_cost_usd"] == 0.0
