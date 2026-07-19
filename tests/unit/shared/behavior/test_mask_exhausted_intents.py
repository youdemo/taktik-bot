"""A spent daily sub-quota removes ITS OWN intent, never the whole plan.

Operator report: with the comment cap reached (12/12) but the action budget at 249/400, the
hourly window at 32/50, the 3h window at 67/100 and follows at 23/30, the account could not
launch at all until the next day. A comment quota says nothing about the right to like, follow
or watch a story — so it now masks the comment intent and the session runs on.
"""

from taktik.core.shared.behavior.interaction_plan import (
    InteractionPlan,
    mask_exhausted_intents,
)


def _plan(**overrides):
    base = dict(
        like_target=3,
        do_follow=True,
        do_comment=True,
        max_comments=2,
        do_watch_story=True,
        story_like_slot=0,
        max_story_slides=3,
        do_story_like=True,
        max_story_likes=2,
    )
    base.update(overrides)
    return InteractionPlan(**base)


def test_spent_comment_quota_masks_only_the_comment():
    plan, masked = mask_exhausted_intents(_plan(), {'comment'})

    assert masked == ['comment']
    assert plan.do_comment is False
    assert plan.max_comments == 0
    # Everything the quota says nothing about survives untouched.
    assert plan.like_target == 3
    assert plan.do_follow is True
    assert plan.do_watch_story is True
    assert plan.do_story_like is True


def test_spent_follow_quota_masks_only_the_follow():
    plan, masked = mask_exhausted_intents(_plan(), {'follow'})

    assert masked == ['follow']
    assert plan.do_follow is False
    assert plan.do_comment is True
    assert plan.like_target == 3


def test_both_quotas_spent_still_leaves_likes_and_stories():
    plan, masked = mask_exhausted_intents(_plan(), {'follow', 'comment'})

    assert sorted(masked) == ['comment', 'follow']
    assert plan.do_follow is False
    assert plan.do_comment is False
    assert plan.like_target == 3
    assert plan.do_watch_story is True


def test_nothing_spent_returns_the_same_plan_object():
    original = _plan()
    plan, masked = mask_exhausted_intents(original, set())

    assert masked == []
    assert plan is original


def test_none_is_treated_as_nothing_spent():
    original = _plan()
    plan, masked = mask_exhausted_intents(original, None)

    assert masked == []
    assert plan is original


def test_masking_an_intent_the_plan_never_had_is_a_noop():
    # The plan already had no comment planned (probability roll) -> nothing to report.
    original = _plan(do_comment=False)
    plan, masked = mask_exhausted_intents(original, {'comment'})

    assert masked == []
    assert plan is original
