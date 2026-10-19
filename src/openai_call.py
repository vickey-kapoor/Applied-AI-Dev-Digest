"""The one place this project talks to the Chat Completions API.

Both model calls want the same three things: a JSON reply, a ceiling on how
long that reply may run, and a run that does not lose the day's digest because
the configured model will not take one of the arguments.

That last one is why this module exists. The model is now chosen by an
environment variable (see OPENAI_MODEL_RANKING in constants), and model
generations disagree about the arguments: `max_tokens` was replaced by
`max_completion_tokens`, and the reasoning models reject `temperature`
outright where the older chat models required it. A pipeline that runs
unattended once a day cannot discover that in production — a 400 there is a
missing digest, and the ranker's own fallback would turn it into a date-ordered
digest that looks exactly like a working one.

So an argument the model refuses is dropped and the call retried, once per
argument, with the drop logged. The reply gets worse in a way we can read in
the log rather than failing in a way nobody sees.
"""

from openai import BadRequestError

from src.logger import get_logger

logger = get_logger(__name__)


# Arguments this module will give up rather than fail on, in the order they
# are worth giving up. `response_format` is first because losing it costs the
# least: both callers still parse a reply that merely claims to be JSON.
# `max_completion_tokens` is last and is never dropped, only renamed — an
# uncapped reply on a reasoning model is an open-ended bill.
_DEGRADABLE = ("response_format", "reasoning_effort", "temperature")

# Worst case: every degradable argument given up, plus the extra step where a
# strict schema degrades to JSON mode before being given up, plus the token
# ceiling's rename, plus the call that finally succeeds.
_MAX_ATTEMPTS = len(_DEGRADABLE) + 3

# Words OpenAI uses when the argument itself is the problem, as opposed to the
# key being wrong or the account being out of quota. Only these are worth
# retrying without the argument; everything else is a real error.
_REFUSAL_WORDS = ("unsupported", "unrecognized", "not supported", "is not permitted")


def _refused_argument(error: BadRequestError, sent: dict) -> str | None:
    """The argument a 400 is complaining about, if that is what it is.

    Matched against what was actually sent rather than a fixed list, so an
    argument added here later is covered without touching this function.
    """
    message = str(getattr(error, "message", "") or error).lower()
    if not any(word in message for word in _REFUSAL_WORDS):
        return None
    for name in ("max_completion_tokens", "max_tokens", *_DEGRADABLE):
        if name in sent and name in message:
            return name
    return None


def json_schema_format(name: str, schema: dict) -> dict:
    """A strict Structured Outputs response_format.

    Strict mode is the point: it makes the reply's *shape* the API's problem
    rather than the parser's. Both callers kept a tolerant parser for replies
    that arrived fenced, prefaced with prose, or in a shape the prompt never
    asked for, and the ranker's tolerance was itself a bug fix (PR #33) for a
    verdict that had been silently falling back to date order. Under a strict
    schema those shapes cannot arrive. The tolerant parsers stay as the path
    for a model or endpoint that will not take the schema.
    """
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": schema},
    }


def call_json(client, *, model: str, prompt: str, max_output_tokens: int, **kwargs):
    """POST one chat completion and return the raw response.

    kwargs are the optional arguments — response_format, temperature,
    reasoning_effort — and any the model refuses are dropped and the call
    retried. None-valued kwargs are not sent at all, so a caller can leave an
    argument out by passing None.

    Returns the SDK response so callers can read finish_reason, which is how a
    reply truncated by the token ceiling is told apart from one the model
    simply wrote badly.
    """
    sent = {k: v for k, v in kwargs.items() if v is not None}
    # max_completion_tokens, not max_tokens: max_tokens is the deprecated
    # spelling and the reasoning models do not accept it. The rename back is
    # handled below for any model that only knows the old name.
    sent["max_completion_tokens"] = max_output_tokens

    # Bounded, so a model that refuses everything terminates instead of looping.
    for _ in range(_MAX_ATTEMPTS):
        try:
            return client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **sent,
            )
        except BadRequestError as e:
            refused = _refused_argument(e, sent)
            if refused is None:
                raise

            if refused == "max_completion_tokens":
                # An older chat model that predates the rename.
                sent.pop("max_completion_tokens")
                sent["max_tokens"] = max_output_tokens
                logger.warning(
                    "%s does not take max_completion_tokens — using max_tokens", model
                )
                continue

            if refused == "response_format":
                fmt = sent.get("response_format") or {}
                if fmt.get("type") == "json_schema":
                    # A schema is better than a promise, but a promise is
                    # better than nothing: both callers still parse JSON mode.
                    sent["response_format"] = {"type": "json_object"}
                    logger.warning(
                        "%s will not take a strict JSON schema — falling back to "
                        "JSON mode, so the reply's shape is the parser's problem again",
                        model,
                    )
                    continue

            sent.pop(refused, None)
            logger.warning("%s will not take %s — retrying without it", model, refused)

    # Unreachable: the loop runs once more than there are arguments to drop.
    raise RuntimeError(f"Could not find a request {model} would accept")


def reply_text(response) -> tuple[str, str | None]:
    """The reply's text and finish_reason, or ("", reason) when it is empty.

    A reasoning model spends its output budget on reasoning tokens before it
    writes anything, so a ceiling sized for the visible answer alone comes back
    with finish_reason "length" and no content at all. The caller logs that
    rather than treating it as a model that answered badly.
    """
    try:
        choice = response.choices[0]
    except (AttributeError, IndexError, TypeError):
        return "", None
    return (choice.message.content or "").strip(), getattr(choice, "finish_reason", None)
