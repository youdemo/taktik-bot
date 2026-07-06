"""A reel must be exited to the grid, never scrolled in-viewer.

Device case (like posts on a profile): opening a REEL from the grid drops the bot in the full-screen
clips viewer. Advancing in-viewer scrolls the REELS FEED (not the profile's posts), and after the
first reel the top-left Back button disappears — trapping the run in an endless reels feed with no
way out (bot stuck, every later workflow failed to navigate to search). The fix: for a reel, exit to
the grid (Back still present on the freshly opened reel) and open another post instead of scrolling.
"""

from taktik.core.social_media.instagram.actions.business.actions.like.post_navigation import (
    PostNavigationMixin,
)
from taktik.core.social_media.instagram.ui.selectors.surfaces.post.detail import POST_SELECTORS

_CLIPS_BACK = '//*[@resource-id="com.instagram.android:id/clips_action_bar_start_action_buttons"]//android.widget.ImageView'


def _nav():
    nav = object.__new__(PostNavigationMixin)
    nav.calls = []
    nav._return_to_grid_and_open_another_post = lambda total=0, username=None: (nav.calls.append('grid') or True)
    nav._navigate_to_next_post_in_sequence = lambda: (nav.calls.append('scroll') or True)
    return nav


def test_reel_exits_to_grid_not_inviewer_scroll():
    nav = _nav()
    nav._advance_or_exit_reel(is_reel=True, total_posts_on_profile=12, username='x')
    assert nav.calls == ['grid'], "a reel must exit to the grid, never scroll the reels feed"


def test_normal_post_advances_in_viewer():
    nav = _nav()
    nav._advance_or_exit_reel(is_reel=False, total_posts_on_profile=12, username='x')
    assert nav.calls == ['scroll'], "a normal post advances in-viewer as before"


def test_reel_exit_propagates_failure():
    nav = _nav()
    nav._return_to_grid_and_open_another_post = lambda total=0, username=None: False
    assert nav._advance_or_exit_reel(is_reel=True) is False, "caller must be able to stop when exit fails"


def test_post_back_selectors_include_the_clips_back_button():
    # The clips/reels viewer Back lives in the clips action bar, not action_bar_button_back;
    # without this selector _return_to_profile_from_post can't leave a reel and falls back to a
    # swipe that doesn't exit the viewer.
    assert _CLIPS_BACK in POST_SELECTORS.back_button_selectors
