"""Language detection must never commit to the WRONG language.

Device bug (2026-07-12, Pixel 6 Pro, Instagram in FRENCH): detection returned
`en (FR=1.5, EN=2.5)`, stripped the French selectors, and `is_on_own_profile` then looked for
"Edit profile" on a screen showing "Modifier le profil" — the bot could never detect its own
account and every session aborted with "Cannot detect active Instagram account".

Two root causes, both covered here:
  1. probes were matched against the RAW XML, which always contains English resource-ids
     (profile_tab, search_tab, action_bar_button_back…) → English got a free, language-
     independent lead on every dump;
  2. no confidence margin → a 2.5-vs-1.5 coin flip was enough to strip a whole locale.
A wrong guess is worse than no guess: 'unknown' keeps every locale (overlay union).
"""

import pytest

from taktik.core.social_media.instagram.ui import language


class _FakeDevice:
    def __init__(self, xml):
        self._xml = xml

    def get_xml_dump(self):
        return self._xml


@pytest.fixture(autouse=True)
def _reset_lang():
    language._detected_lang = None
    yield
    language._detected_lang = None


# The English resource-ids that are present on EVERY Instagram dump, whatever the app language.
_ENGLISH_IDS = (
    '<node resource-id="com.instagram.android:id/profile_tab" />'
    '<node resource-id="com.instagram.android:id/search_tab" />'
    '<node resource-id="com.instagram.android:id/feed_tab" />'
    '<node resource-id="com.instagram.android:id/action_bar_button_back" />'
    '<node resource-id="com.instagram.android:id/activity_feed" />'
)


def test_english_resource_ids_alone_never_decide_the_language():
    """The exact regression: an English-id-only dump used to score EN=2.5 and win."""
    assert language.detect_language(_FakeDevice(_ENGLISH_IDS)) == 'unknown'


def test_french_app_with_english_resource_ids_is_detected_french():
    """A French nav bar must win despite the English ids sitting in the same dump."""
    xml = _ENGLISH_IDS + (
        '<node content-desc="Accueil" />'
        '<node content-desc="Rechercher et explorer" />'
        '<node content-desc="Profil" />'
        '<node text="Modifier le profil" />'
    )
    assert language.detect_language(_FakeDevice(xml)) == 'fr'


def test_english_app_is_detected_english():
    xml = _ENGLISH_IDS + (
        '<node content-desc="Home" />'
        '<node content-desc="Search" />'
        '<node content-desc="Profile" />'
        '<node text="Edit profile" />'
    )
    assert language.detect_language(_FakeDevice(xml)) == 'en'


def test_profil_does_not_score_on_the_english_word_profile():
    """Whole-word matching: FR 'Profil' must not be found inside EN 'Profile'."""
    values = ['Profile', 'Edit profile']
    assert language._score_probes(['Profil'], values) == 0.0
    assert language._score_probes(['Profile'], values) == 1.0


def test_a_poor_screen_stays_unknown_instead_of_guessing():
    """The screen the bot actually started on: barely any visible words → keep every locale."""
    xml = _ENGLISH_IDS + '<node text="15:31" /><node content-desc="Les plus récents" />'
    assert language.detect_language(_FakeDevice(xml)) == 'unknown'


def test_ambiguous_scores_stay_unknown():
    """Close scores must not strip a locale (the 2.5-vs-1.5 coin flip)."""
    xml = '<node content-desc="Accueil" /><node content-desc="Home" />'
    assert language.detect_language(_FakeDevice(xml)) == 'unknown'


def test_unknown_keeps_all_selectors(monkeypatch):
    """'unknown' must not run the in-place filtering (that is what protects a bad detection)."""
    removed = []
    monkeypatch.setattr(language, 'optimize_selector_dataclass',
                        lambda inst, lang: removed.append(lang) or 0)
    lang = language.detect_and_optimize(_FakeDevice(_ENGLISH_IDS))
    assert lang == 'unknown'
    assert removed == []  # no locale was stripped
