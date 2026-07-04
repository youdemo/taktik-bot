"""Blocking-modal signatures — the single source of truth for UNEXPECTED sheets/dialogs that a
mis-tap can open and that would silently BLOCK a workflow.

A "blocking modal" is a surface that no interaction phase (like / comment / follow / story)
legitimately opens — e.g. the Direct "Send post" share sheet triggered by a mis-tap on the share
button that sits next to the comment button. The interaction engine checks for these proactively
between action phases and backs out of them; the comment action and the workflow watchdog reuse
the same signatures as a safety net.

Keyed off framework / IG resource-ids (never localized @text), so detection holds across app
languages; contains() absorbs version drift. To cover a newly-observed blocker, add ONE signature
here and every consumer picks it up.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


def _contains(fragment: str) -> str:
    """XPath that matches any node whose resource-id contains `fragment`."""
    return f'//*[contains(@resource-id, "{fragment}")]'


@dataclass
class BlockingModalSelectors:
    """Language-independent signatures of blocking modals + helpers to build queries from them."""

    # Each signature: a stable `name`, a human `label`, and the resource-id `fragments` that
    # identify the modal (any one present => the modal is on screen).
    signatures: List[Dict[str, object]] = field(default_factory=lambda: [
        {
            "name": "direct_share_sheet",
            "label": "Direct share sheet",
            "fragments": [
                "direct_private_share_container_view",
                "direct_private_share_recipients_recycler_view",
                "direct_private_share_search_box",
                "direct_external_share_container_view",
            ],
        },
    ])

    def signature_xpath_list(self, name: str) -> List[str]:
        """Per-fragment xpath indicators for one named signature (list form, for legacy consumers)."""
        sig = next((s for s in self.signatures if s["name"] == name), None)
        if not sig:
            return []
        return [_contains(f) for f in sig["fragments"]]

    def signature_xpath(self, name: str) -> str:
        """Single OR-query for one named signature (used to identify which modal matched)."""
        return ' | '.join(self.signature_xpath_list(name))

    def xpath_indicators(self) -> List[str]:
        """Flat list of every per-fragment xpath indicator across all signatures."""
        return [_contains(f) for sig in self.signatures for f in sig["fragments"]]

    def combined_xpath(self) -> str:
        """One OR-query across every blocking-modal indicator (single UI round-trip)."""
        return ' | '.join(self.xpath_indicators())

    @property
    def all_resource_id_fragments(self) -> List[str]:
        """Raw resource-id fragments — for XML-substring consumers such as the watchdog."""
        return [f for sig in self.signatures for f in sig["fragments"]]

    def identify(self, exists_fn) -> Optional[str]:
        """Return the name of the first signature that `exists_fn(xpath)` reports present, else None.

        `exists_fn` takes a combined xpath string and returns a bool (e.g. a wrapper over
        device.xpath(q).exists). Kept UI-agnostic so it is trivially unit-testable."""
        for sig in self.signatures:
            if exists_fn(self.signature_xpath(sig["name"])):
                return str(sig["name"])
        return None


BLOCKING_MODAL_SELECTORS = BlockingModalSelectors()
