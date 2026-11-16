"""Evidence screening for the requested tracks, not semantic outcome grading."""
from datetime import datetime
import os
import re
from zoneinfo import ZoneInfo


def discord_in_period(timestamp):
    if not isinstance(timestamp, str):
        return False
    try:
        date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if date.tzinfo is None:
        return False  # Do not guess an export's timezone.
    local = date.astimezone(ZoneInfo(os.environ.get("INTERACTION_FOUNDRY_DISCORD_TIMEZONE", "UTC"))).date()
    start = os.environ.get("INTERACTION_FOUNDRY_DISCORD_START")
    end = os.environ.get("INTERACTION_FOUNDRY_DISCORD_END")
    if start and local < datetime.fromisoformat(start).date():
        return False
    if end and local >= datetime.fromisoformat(end).date():
        return False
    return True


FRICTION = {
    "repeated_constraint": r"\b(already (?:told|said|asked)|keep (?:telling|asking)|again and again|how many times)\b",
    "missing_follow_through": r"\b(actually (?:do|implement|fix)|stop (?:asking|planning)|instead of (?:doing|implementing)|did(?:n't| not) (?:do|finish))\b",
    "unverified_completion": r"\b(still (?:broken|doesn.t work)|you (?:said|claimed).{0,50}(?:done|fixed)|not (?:actually )?(?:tested|verified))\b",
    "scope_or_context_loss": r"\b(not what I asked|forgot|forgetting|lost (?:the )?context|wrong (?:file|project|version))\b",
    "repeated_failed_repair": r"\b(same (?:error|problem|issue)|still failing|tried (?:that|this) already)\b",
}
CONTINUE = re.compile(r"^\s*(?:please\s+)?(?:continue|keep going|resume|go on)(?:\s+(?:where you left off|please))?[.!\s]*$", re.I)


def friction_signals(text):
    if CONTINUE.fullmatch(text):
        return []
    # Quoted blocks/code must be semantically attributed before counting.
    unquoted = re.sub(r"```.*?```", "", text, flags=re.S)
    unquoted = "\n".join(line for line in unquoted.splitlines() if not line.lstrip().startswith(">"))
    return [name for name, pattern in FRICTION.items() if re.search(pattern, unquoted, re.I)]


def stop_signal(previous_text):
    """Return candidate cause only; source context/tool evidence must confirm it."""
    signals = {
        "platform_limit": r"usage limit|rate.limit|context (?:window|limit)|quota|token budget",
        "approval_boundary": r"permission|approval|authorize",
        "missing_information": r"need.{0,30}(?:path|file|credential|information)",
        "premature_handoff_candidate": r"would you like me to|should I continue|if you.d like.{0,20}(?:can|will)",
    }
    return [label for label, pattern in signals.items() if re.search(pattern, previous_text, re.I)] or ["unknown"]


def social_signals(message, target_ids):
    """Return review candidates; reactions alone do not establish positive sentiment."""
    if not discord_in_period(message.get("timestamp")):
        return []
    author = str((message.get("author") or {}).get("id", ""))
    if author in target_ids:
        return ["received_reactions_needs_attribution"] if message.get("reactions") else []
    body = message.get("content", "")
    result = []
    if re.search(r"\b(thanks|thank you|appreciate|helpful|well done|great work)\b", body, re.I):
        result.append("positive_response_needs_target_link")
    if re.search(r"\b(lol|lmao|haha|hilarious)\b|[😂🤣]", body, re.I):
        result.append("amusement_needs_context")
    return result
