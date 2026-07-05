"""generate_smart_comment returns a {reasoning, comment} pair so the Agent card can show WHY the
comment was written (decision context, also feeds the autonomous-mode trace).

The model is asked for a single-line JSON object; parsing must be robust and fall back to
"whole text = comment" when the model doesn't comply (backward compatible).
"""

from taktik.core.app.ai.providers.openrouter import AIService


def _service(monkeypatch, model_text):
    # Bypass __init__: we only exercise the parsing, with ipc disabled and text_completion stubbed.
    svc = object.__new__(AIService)
    svc.ipc = None
    svc.text_model = "test/model"
    svc.niche_taxonomy = {}
    monkeypatch.setattr(
        svc, "text_completion",
        lambda *a, **k: {"success": True, "text": model_text, "model": "test/model", "cost_usd": 0.0},
    )
    return svc


def test_parses_reasoning_and_comment_from_json(monkeypatch):
    svc = _service(
        monkeypatch,
        '{"reasoning": "Le post annonce une retraite; je réagis à l\'invitation avec enthousiasme.", '
        '"comment": "Ça donne trop envie ce moment 🙌"}',
    )
    out = svc.generate_smart_comment(post_description="a retreat announcement", username="x",
                                     language="fr", app_language="fr")
    assert out["success"] is True
    assert out["comment"] == "Ça donne trop envie ce moment 🙌"
    assert "retraite" in out["reasoning"]


def test_json_with_surrounding_text_is_still_parsed(monkeypatch):
    svc = _service(monkeypatch, 'Sure!\n{"reasoning": "why", "comment": "love this vibe ✨"}\nHope that helps')
    out = svc.generate_smart_comment(post_description="d", username="x", language="en", app_language="en")
    assert out["comment"] == "love this vibe ✨"
    assert out["reasoning"] == "why"


def test_fallback_when_not_json(monkeypatch):
    # The model ignored the JSON instruction and returned a bare comment -> use it as the comment.
    svc = _service(monkeypatch, "just a plain comment no json 🔥")
    out = svc.generate_smart_comment(post_description="d", username="x", language="en", app_language="en")
    assert out["comment"] == "just a plain comment no json 🔥"
    assert out["reasoning"] == ""


def test_strips_wrapping_quotes_in_fallback(monkeypatch):
    svc = _service(monkeypatch, '"quoted plain comment"')
    out = svc.generate_smart_comment(post_description="d", username="x", language="en", app_language="en")
    assert out["comment"] == "quoted plain comment"
