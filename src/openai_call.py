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


def _int_or_none(value) -> int | None:
    """The value when it is a real integer, else None.

    The usage block is optional in the API and absent from the stubs used in
    tests, where attribute access returns a mock rather than a number. A
    number is logged; anything else is simply not mentioned.
    """
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def log_usage(model: str, response) -> dict:
    """Log what the call cost in tokens, and return the numbers.

    The digest makes two model calls a day and recorded nothing about either,
    so the only answer to "what does this cost" was an estimate from the
    prompt's length. Reasoning tokens are the reason it matters more than it
    used to: they are billed as output and are invisible in the reply, so a
    model switch can multiply the bill with nothing in the log to show it.
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}

    numbers = {
        "prompt": _int_or_none(getattr(usage, "prompt_tokens", None)),
        "completion": _int_or_none(getattr(usage, "completion_tokens", None)),
        "total": _int_or_none(getattr(usage, "total_tokens", None)),
    }

    completion_details = getattr(usage, "completion_tokens_details", None)
    numbers["reasoning"] = _int_or_none(
        getattr(completion_details, "reasoning_tokens", None)
    )
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    numbers["cached"] = _int_or_none(getattr(prompt_details, "cached_tokens", None))

    reported = {k: v for k, v in numbers.items() if v is not None}
    if not reported:
        return {}

    logger.info(
        "%s token usage: %s",
        model,
        ", ".join(f"{name}={count}" for name, count in reported.items()),
    )
    return reported


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
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **sent,
            )
            # Never at the cost of the digest: this is bookkeeping, and a
            # surprise in the usage block must not lose a reply already paid
            # for.
            try:
                log_usage(model, response)
            except Exception as e:
                logger.warning("Could not read token usage: %s", e)
            return response
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
