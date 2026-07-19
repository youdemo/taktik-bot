"""List-level relationship read: each follower ROW carries an action button whose caption reveals
our relationship (Suivre / Suivi(e) / Suivre en retour), so we can skip an already-related follower
WITHOUT opening the profile. get_row_follow_state pairs a username to its row button by vertical
bounds and classifies the caption via the shared locale labels. Fail-open ('unknown') when a row is
unreadable / partially scrolled, so a valid target is never lost.
"""

import types

import pytest

from taktik.core.social_media.instagram.actions.atomic.detection.list_detection import (
    ListDetectionMixin,
)
from taktik.core.social_media.instagram.ui.selectors.locales import set_active_locale


@pytest.fixture(autouse=True)
def _reset_locale():
    set_active_locale(None)
    yield
    set_active_locale(None)


class _El:
    def __init__(self, text, bounds):
        self.text = text
        self.bounds = bounds  # (left, top, right, bottom)


class _Result:
    def __init__(self, els):
        self._els = els

    @property
    def exists(self):
        return len(self._els) > 0

    def all(self):
        return self._els


class _Device:
    """Routes the two xpath queries get_row_follow_state makes: usernames vs row buttons."""

    def __init__(self, names, btns):
        self._names = names
        self._btns = btns

    def xpath(self, selector):
        if "follow_list_row_large_follow_button" in selector:
            return _Result(self._btns)
        if "follow_list_username" in selector:
            return _Result(self._names)
        return _Result([])


class _NoopLogger:
    def debug(self, *a, **k):
        return None


def _host(names, btns):
    host = object.__new__(ListDetectionMixin)
    host.device = _Device(names, btns)
    host.detection_selectors = types.SimpleNamespace(
        follow_list_username_selectors=['//*[@resource-id="com.instagram.android:id/follow_list_username"]']
    )
    host.logger = _NoopLogger()
    host._clean_username = lambda u: (u or "").strip()
    return host


def _rows(locale):
    """Three clean rows (name centre inside its button's y-band) + one row whose button is missing
    (partially scrolled) — that last one must fail open to 'unknown'."""
    set_active_locale(locale)
    fr = locale != "en"
    names = [
        _El("alice", (0, 100, 300, 140)),   # yc 120
        _El("bob", (0, 200, 300, 240)),     # yc 220
        _El("carol", (0, 300, 300, 340)),   # yc 320
        _El("dave", (0, 400, 300, 440)),    # yc 420 — button missing below
    ]
    btns = [
        _El("Suivi(e)" if fr else "Following", (400, 100, 600, 150)),
        _El("Suivre en retour" if fr else "Follow back", (400, 200, 600, 250)),
        _El("Suivre" if fr else "Follow", (400, 300, 600, 350)),
        # no button overlapping y≈420 (dave's row scrolled past the bottom)
    ]
    return names, btns


@pytest.mark.parametrize("locale", ["fr", "en", None])
def test_reads_each_relationship_from_the_row(locale):
    names, btns = _rows(locale)
    host = _host(names, btns)
    assert host.get_row_follow_state("alice") == "following"
    assert host.get_row_follow_state("bob") == "follow_back"
    assert host.get_row_follow_state("carol") == "follow"


@pytest.mark.parametrize("locale", ["fr", "en", None])
def test_fail_open_when_row_button_missing(locale):
    names, btns = _rows(locale)
    host = _host(names, btns)
    assert host.get_row_follow_state("dave") == "unknown"


def test_fail_open_for_unknown_username():
    names, btns = _rows("fr")
    host = _host(names, btns)
    assert host.get_row_follow_state("nobody") == "unknown"


def test_no_rows_is_unknown():
    host = _host([], [])
    assert host.get_row_follow_state("alice") == "unknown"
