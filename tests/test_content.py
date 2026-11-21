"""Hook, caption, hashtag and caption-beat rules."""

import pytest

from core.content import (
    CampaignRules,
    Moment,
    PlatformRules,
    PolicyError,
    build_package,
    plan_caption_beats,
)

PLATFORM = PlatformRules(name="short-video", max_hashtags=5, max_caption_chars=150)
OPEN_CAMPAIGN = CampaignRules(name="open")
CAMPAIGN = CampaignRules(
    name="Example campaign",
    required_tags=("#ExampleCampaign", "#GTA6"),
    required_caption_lines=("Watch the full stream on the creator's channel",),
    credit_line="Credit: @creator",
)


def moment(**overrides):
    values = dict(subject="Alex", game="GTA 6", kind="reaction", event="a sudden police chase",
                  labels=("chase",), ai_generated=False)
    values.update(overrides)
    return Moment(**values)


def test_hook_uses_only_the_verified_event():
    package = build_package(moment(), OPEN_CAMPAIGN, PLATFORM)
    assert package.hook == "Alex reacts to a sudden police chase"
    assert package.warnings == []


def test_without_a_verified_event_a_neutral_hook_is_used_and_flagged():
    package = build_package(moment(event=None), OPEN_CAMPAIGN, PLATFORM)
    assert package.hook in ("Wait for it.", "Watch until the end.", "You need to see this.")
    assert any("no verified event" in w for w in package.warnings)


def test_every_package_needs_a_persons_approval():
    assert build_package(moment(), OPEN_CAMPAIGN, PLATFORM).needs_review is True


def test_ai_footage_is_refused_for_a_campaign_that_does_not_allow_it():
    with pytest.raises(PolicyError):
        build_package(moment(ai_generated=True), CAMPAIGN, PLATFORM)


def test_campaign_tags_are_never_dropped_even_at_the_limit():
    tight = PlatformRules(name="tight", max_hashtags=2)
    package = build_package(moment(labels=("chase", "crash", "wild")), CAMPAIGN, tight)
    assert package.hashtags == ["#ExampleCampaign", "#GTA6"]


def test_too_many_campaign_tags_for_a_platform_is_a_policy_error():
    tight = PlatformRules(name="tight", max_hashtags=1)
    with pytest.raises(PolicyError):
        build_package(moment(), CAMPAIGN, tight)


def test_hashtags_are_normalised_and_deduplicated():
    package = build_package(moment(labels=("Chase", "chase!", "crash scene")), OPEN_CAMPAIGN, PLATFORM)
    assert package.hashtags == ["#GTA6", "#Alex", "#Chase", "#crashscene"]


def test_caption_keeps_campaign_lines_and_credit_in_order():
    package = build_package(moment(), CAMPAIGN, PLATFORM)
    assert package.caption == (
        "A sudden police chase. Watch the full stream on the creator's channel. Credit: @creator."
    )


def test_claim_words_are_flagged_for_a_person_to_check():
    package = build_package(moment(event="the first ever run"), OPEN_CAMPAIGN, PLATFORM)
    assert any("first" in w for w in package.warnings)


def test_text_puts_hook_caption_and_tags_on_separate_lines():
    package = build_package(moment(), CAMPAIGN, PLATFORM)
    lines = package.text().split("\n\n")
    assert lines[0] == package.hook
    assert lines[1] == package.caption
    assert lines[2] == " ".join(package.hashtags)


def test_caption_beats_for_a_twenty_second_clip_with_four_phrases():
    phrases = ["TRAILER. GAME. REACTION.", "CLIP THAT.", "PUNCH INTO THE REACTION.", "READY TO DROP."]
    beats = plan_caption_beats(20.0, phrases)
    assert [(b.start_s, b.end_s) for b in beats] == [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0), (15.0, 20.0)]
    assert beats[0].text == "TRAILER. GAME. REACTION."


def test_caption_beats_refuse_too_many_or_too_few_phrases():
    with pytest.raises(ValueError, match="too many"):
        plan_caption_beats(4.0, ["a", "b", "c"])
    with pytest.raises(ValueError, match="too few"):
        plan_caption_beats(60.0, ["one", "two"])


def test_caption_beats_refuse_long_phrases():
    with pytest.raises(ValueError, match="more than 5 words"):
        plan_caption_beats(10.0, ["this caption has far too many words in it"])
