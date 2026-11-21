"""Post text and on-screen captions, with campaign and safety rules.

Every line is built from facts a person has verified and entered. Nothing is guessed. A
post package always needs a person's approval before it is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_HOOK_WORDS = 8
MAX_CAPTION_WORDS_ON_SCREEN = 5

# Words that claim something. They are flagged, so a person checks the claim first.
CLAIM_WORDS = frozenset(
    {"first", "best", "only", "record", "world", "exclusive", "leak", "leaked", "insider",
     "confirmed", "official", "biggest", "fastest"}
)

# Used when no verified event exists. They claim nothing about the footage.
NEUTRAL_HOOKS = ("Wait for it.", "Watch until the end.", "You need to see this.")

HOOK_TEMPLATES = {
    "reaction": "{subject} reacts to {event}",
    "clutch": "{subject} pulls off {event}",
    "fail": "{subject} messes up {event}",
    "highlight": "{subject}: {event}",
    "funny": "{subject}: {event}",
}


class PolicyError(ValueError):
    """A rule that must not be broken, such as a campaign rule."""


@dataclass(frozen=True)
class CampaignRules:
    name: str
    required_tags: tuple[str, ...] = ()
    required_caption_lines: tuple[str, ...] = ()
    credit_line: str | None = None
    ai_content_allowed: bool = False


@dataclass(frozen=True)
class PlatformRules:
    name: str
    max_hashtags: int = 5
    max_caption_chars: int = 150


@dataclass(frozen=True)
class Moment:
    subject: str
    game: str
    kind: str
    event: str | None
    labels: tuple[str, ...] = ()
    ai_generated: bool = False


@dataclass
class PostPackage:
    hook: str
    caption: str
    hashtags: list[str]
    warnings: list[str] = field(default_factory=list)
    needs_review: bool = True  # always: a person approves before posting

    def text(self) -> str:
        tags = " ".join(self.hashtags)
        return "\n\n".join(part for part in (self.hook, self.caption, tags) if part)


@dataclass(frozen=True)
class Beat:
    start_s: float
    end_s: float
    text: str


def normalise_tag(raw: str) -> str | None:
    """'#Chase Scene!' -> '#ChaseScene'. Returns None if nothing is left."""
    tag = re.sub(r"[^A-Za-z0-9_]", "", raw.strip().lstrip("#"))
    return f"#{tag}" if tag else None


def _claims_in(text: str) -> list[str]:
    words = {w.lower() for w in re.findall(r"[A-Za-z']+", text)}
    return sorted(words & CLAIM_WORDS)


def _sentence(text: str) -> str:
    text = text.strip()
    text = text[:1].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."


def build_hook(moment: Moment, index: int = 0) -> tuple[str, list[str]]:
    if moment.kind not in HOOK_TEMPLATES:
        raise ValueError(f"unknown moment kind {moment.kind!r}")
    warnings: list[str] = []
    if moment.event is None:
        warnings.append(
            "no verified event: a neutral hook was used. Add a verified event for a specific hook"
        )
        hook = NEUTRAL_HOOKS[index % len(NEUTRAL_HOOKS)]
    else:
        template = HOOK_TEMPLATES[moment.kind]
        hook = template.format(subject=moment.subject.strip(), event=moment.event.strip())
    words = len(hook.split())
    if words > MAX_HOOK_WORDS:
        warnings.append(f"the hook is {words} words; keep it under {MAX_HOOK_WORDS}")
    return hook, warnings


def build_hashtags(
    moment: Moment, campaign: CampaignRules, platform: PlatformRules, *, extra: tuple[str, ...] = ()
) -> list[str]:
    """Campaign tags always stay. The rest fill up to the platform's limit, without duplicates."""
    required = [t for t in (normalise_tag(raw) for raw in campaign.required_tags) if t]
    if len(required) > platform.max_hashtags:
        raise PolicyError(
            f"the campaign '{campaign.name}' needs {len(required)} hashtags; "
            f"{platform.name} allows {platform.max_hashtags}"
        )
    candidates = [moment.game, moment.subject, *moment.labels, *extra]
    optional = [t for t in (normalise_tag(raw) for raw in candidates) if t]
    result: list[str] = []
    seen: set[str] = set()
    for tag in [*required, *optional]:
        key = tag.lower()
        if key in seen:
            continue
        if len(result) >= platform.max_hashtags and tag not in required:
            break
        seen.add(key)
        result.append(tag)
    return result


def build_caption(moment: Moment, campaign: CampaignRules) -> str:
    parts: list[str] = []
    if moment.event:
        parts.append(_sentence(moment.event))
    parts.extend(_sentence(line) for line in campaign.required_caption_lines)
    if campaign.credit_line:
        parts.append(_sentence(campaign.credit_line))
    return " ".join(parts)


def build_package(
    moment: Moment,
    campaign: CampaignRules,
    platform: PlatformRules,
    *,
    hook_index: int = 0,
    extra_tags: tuple[str, ...] = (),
) -> PostPackage:
    if moment.ai_generated and not campaign.ai_content_allowed:
        raise PolicyError(
            f"the campaign '{campaign.name}' does not allow AI-generated footage or voices, "
            "and this clip has them"
        )
    hook, warnings = build_hook(moment, hook_index)
    caption = build_caption(moment, campaign)
    if len(caption) > platform.max_caption_chars:
        warnings.append(
            f"the caption is {len(caption)} characters; "
            f"{platform.name} shows about {platform.max_caption_chars}"
        )
    claims = _claims_in(f"{hook} {caption}")
    if claims:
        warnings.append("check these claim words before posting: " + ", ".join(claims))
    hashtags = build_hashtags(moment, campaign, platform, extra=extra_tags)
    return PostPackage(hook=hook, caption=caption, hashtags=hashtags, warnings=warnings)


def plan_caption_beats(
    duration_s: float,
    phrases: list[str],
    *,
    min_seconds: float = 2.5,
    max_seconds: float = 6.0,
    max_words: int = MAX_CAPTION_WORDS_ON_SCREEN,
) -> list[Beat]:
    """Split a clip into equal on-screen caption beats. Each phrase is one beat."""
    if not phrases:
        raise ValueError("at least one caption phrase is needed")
    for phrase in phrases:
        if len(phrase.split()) > max_words:
            raise ValueError(f"caption {phrase!r} has more than {max_words} words")
    if duration_s <= 0:
        raise ValueError("the clip must be longer than zero seconds")
    each = duration_s / len(phrases)
    if each < min_seconds:
        raise ValueError(
            f"{len(phrases)} captions on {duration_s:.1f} s is too many; "
            f"each beat would be under {min_seconds} s"
        )
    if each > max_seconds:
        raise ValueError(
            f"{len(phrases)} captions on {duration_s:.1f} s is too few; "
            f"each beat would be over {max_seconds} s"
        )
    beats: list[Beat] = []
    start = 0.0
    for phrase in phrases:
        end = start + each
        beats.append(Beat(round(start, 2), round(end, 2), phrase))
        start = end
    return beats
