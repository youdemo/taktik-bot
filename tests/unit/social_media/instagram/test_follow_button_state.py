"""Anti-regression: the profile-header button must reveal the REAL relationship.

Background (2026-07-18): a Target run re-interacted with profiles that already followed the
operated account. Root cause: `get_follow_button_state()` matched the button text against
hardcoded stems in this order -> ('following', 'abonné', 'suivi') then ('follow', 'suivre').
A "Suivre en retour" button contains "suivre" but NOT "suivi", so it fell through to the
'follow' branch and an existing follower was read as a brand-new target. Same in English:
"Follow back" contains "follow". The 'follow_back' state simply did not exist.

Fixtures are anonymized minimal extracts of REAL IG v410 UI dumps (FR + EN) captured on device,
including the `profile_header_follow_context_text` decoy ("Suivi(e) par X, Y" = mutual friends),
a NON-clickable TextView sitting just above the button — a bare text match hits it instead of
the button.
"""

from lxml import etree

from taktik.core.social_media.instagram.actions.atomic.interaction.profile_interaction import (
    ProfileInteractionMixin,
)
from taktik.core.social_media.instagram.ui.selectors.locales import set_active_locale
from taktik.core.social_media.instagram.ui.selectors.surfaces.profile import PROFILE_SELECTORS


class _XPathResult:
    def __init__(self, nodes):
        self._nodes = nodes

    @property
    def exists(self) -> bool:
        return len(self._nodes) > 0

    def get_text(self):
        if not self._nodes:
            return None
        return self._nodes[0].get("text")


class _XmlDevice:
    def __init__(self, xml: str):
        self._tree = etree.fromstring(xml.encode("utf-8"))

    def xpath(self, selector: str) -> _XPathResult:
        return _XPathResult(self._tree.xpath(selector))


class _NoopLogger:
    def debug(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None


class _Reader(ProfileInteractionMixin):
    """Minimal host: the state read only needs `device` + the selectors property."""

    def __init__(self, xml: str):
        self.device = _XmlDevice(xml)
        self.logger = _NoopLogger()

    @property
    def profile_selectors(self):
        return PROFILE_SELECTORS

    def _is_element_present(self, _selectors) -> bool:
        # The Message-button fallback is out of scope here; force the button read to decide.
        return False


def _profile(button_text: str, context_text: str = "") -> str:
    """A profile header carrying the action button and, optionally, the mutual-friends decoy."""
    decoy = (
        f'<node resource-id="com.instagram.android:id/profile_header_follow_context_text"'
        f' class="android.widget.TextView" clickable="false" text="{context_text}" />'
        if context_text
        else ""
    )
    return f"""
<hierarchy>
  <node resource-id="com.instagram.android:id/row_profile_header">
    {decoy}
    <node resource-id="com.instagram.android:id/profile_header_follow_button"
          class="android.widget.Button" clickable="true" text="{button_text}" />
  </node>
</hierarchy>
"""


# ── The bug: a profile that already follows US ────────────────────────────────────

def test_fr_follow_back_is_not_read_as_a_fresh_target():
    set_active_locale("fr")
    reader = _Reader(_profile("Suivre en retour"))
    assert reader.get_follow_button_state() == "follow_back"


def test_en_follow_back_is_not_read_as_a_fresh_target():
    set_active_locale("en")
    reader = _Reader(_profile("Follow back"))
    assert reader.get_follow_button_state() == "follow_back"


# ── We already follow THEM ────────────────────────────────────────────────────────

def test_fr_following():
    set_active_locale("fr")
    assert _Reader(_profile("Suivi(e)")).get_follow_button_state() == "following"


def test_en_following():
    set_active_locale("en")
    assert _Reader(_profile("Following")).get_follow_button_state() == "following"


# ── No relationship: the normal target ────────────────────────────────────────────

def test_fr_plain_follow():
    set_active_locale("fr")
    assert _Reader(_profile("Suivre")).get_follow_button_state() == "follow"


def test_en_plain_follow():
    set_active_locale("en")
    assert _Reader(_profile("Follow")).get_follow_button_state() == "follow"


# ── The mutual-friends decoy must never drive the verdict ─────────────────────────

def test_mutual_friends_label_does_not_flip_a_fresh_target():
    """"Suivi(e) par X, Y" sits above a plain "Suivre" button: the state stays 'follow'."""
    set_active_locale("fr")
    xml = _profile("Suivre", context_text="Suivi(e) par cikadermo, giustiinaa et 21 autres")
    assert _Reader(xml).get_follow_button_state() == "follow"


def test_mutual_friends_label_does_not_mask_follow_back():
    set_active_locale("en")
    xml = _profile("Follow back", context_text="Followed by amandine_meolia and 21 others")
    assert _Reader(xml).get_follow_button_state() == "follow_back"


# ── Locale-agnostic safety net ────────────────────────────────────────────────────

def test_states_hold_without_language_detection():
    """If detect_and_optimize never ran, L() falls back to the multi-language union.

    The state labels are disjoint across languages, so the ordered detection still holds — a
    Lab run (or any path missing the locale setup) must not report a different state.
    """
    set_active_locale(None)
    assert _Reader(_profile("Suivre en retour")).get_follow_button_state() == "follow_back"
    assert _Reader(_profile("Follow back")).get_follow_button_state() == "follow_back"
    assert _Reader(_profile("Suivi(e)")).get_follow_button_state() == "following"
    assert _Reader(_profile("Following")).get_follow_button_state() == "following"
    assert _Reader(_profile("Suivre")).get_follow_button_state() == "follow"
    assert _Reader(_profile("Follow")).get_follow_button_state() == "follow"
