"""Unit tests for the shared Chat Completions call layer.

The point of this layer is that the model is now an environment variable, so
the pipeline can be pointed at a model generation that does not take the same
arguments. A once-a-day unattended job cannot find that out in production:
a 400 there is a missing digest, and the ranker's own fallback would turn it
into a date-ordered digest nobody can tell from a ranked one.
"""

import httpx
import pytest
from unittest.mock import Mock, patch

from openai import AuthenticationError, BadRequestError

from src.openai_call import (
    _MAX_ATTEMPTS,
    call_json,
    json_schema_format,
    reply_text,
)


SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def _http_error(status: int, message: str, cls):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return cls(message, response=httpx.Response(status, request=request), body=None)


def bad_request(message: str) -> BadRequestError:
    return _http_error(400, message, BadRequestError)


def _ok_response(content: str = '{"answer": "yes"}', finish_reason: str = "stop"):
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = content
    response.choices[0].finish_reason = finish_reason
    return response


def _client(*side_effects):
    """A client whose create() raises each side effect in turn, then succeeds."""
    client = Mock()
    client.chat.completions.create.side_effect = list(side_effects) + [_ok_response()]
    return client


def _call(client, **kwargs):
    return call_json(
        client,
        model="test-model",
        prompt="prompt",
        max_output_tokens=16000,
        **kwargs,
    )


class TestTheHappyPath:
    def test_sends_the_prompt_as_a_user_message(self):
        client = _client()
        _call(client)

        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "test-model"
        assert kwargs["messages"] == [{"role": "user", "content": "prompt"}]

    def test_caps_the_reply_with_max_completion_tokens(self):
        """max_tokens is the deprecated spelling; the reasoning models reject it."""
        client = _client()
        _call(client)

        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["max_completion_tokens"] == 16000
        assert "max_tokens" not in kwargs

    def test_a_none_argument_is_not_sent_at_all(self):
        """So a caller can leave reasoning_effort to the model's own default."""
        client = _client()
        _call(client, reasoning_effort=None, temperature=0)

        kwargs = client.chat.completions.create.call_args.kwargs
        assert "reasoning_effort" not in kwargs
        assert kwargs["temperature"] == 0

    def test_one_call_when_nothing_is_refused(self):
        client = _client()
        _call(client, temperature=0)
        assert client.chat.completions.create.call_count == 1


class TestArgumentsTheModelRefuses:
    """Each one is dropped and the call retried, rather than losing the digest."""

    def test_temperature_is_dropped(self):
        """The reasoning models reject temperature where the chat models required it."""
        client = _client(bad_request("Unsupported parameter: 'temperature'"))

        _call(client, temperature=0)

        assert client.chat.completions.create.call_count == 2
        assert "temperature" not in client.chat.completions.create.call_args.kwargs

    def test_reasoning_effort_is_dropped(self):
        client = _client(
            bad_request("Unrecognized request argument supplied: reasoning_effort")
        )

        _call(client, reasoning_effort="low")

        assert "reasoning_effort" not in client.chat.completions.create.call_args.kwargs

    def test_a_strict_schema_degrades_to_json_mode_before_being_given_up(self):
        """A promise of JSON is worse than a schema and better than nothing:
        both callers still parse a reply that only claims to be JSON."""
        client = _client(
            bad_request("Unsupported parameter: 'response_format.json_schema'")
        )

        _call(client, response_format=json_schema_format("answer", SCHEMA))

        fmt = client.chat.completions.create.call_args.kwargs["response_format"]
        assert fmt == {"type": "json_object"}

    def test_json_mode_is_dropped_if_it_is_refused_too(self):
        client = _client(
            bad_request("Unsupported parameter: 'response_format.json_schema'"),
            bad_request("Unsupported parameter: 'response_format'"),
        )

        _call(client, response_format=json_schema_format("answer", SCHEMA))

        assert "response_format" not in client.chat.completions.create.call_args.kwargs

    def test_the_token_ceiling_is_renamed_rather_than_dropped(self):
        """An uncapped reply on a reasoning model is an open-ended bill."""
        client = _client(bad_request("Unsupported parameter: 'max_completion_tokens'"))

        _call(client)

        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["max_tokens"] == 16000
        assert "max_completion_tokens" not in kwargs

    def test_several_refusals_in_a_row_all_resolve(self):
        client = _client(
            bad_request("Unsupported parameter: 'temperature'"),
            bad_request("Unsupported value: 'response_format' is not supported"),
            bad_request("Unrecognized request argument supplied: reasoning_effort"),
        )

        _call(
            client,
            temperature=0,
            reasoning_effort="low",
            response_format=json_schema_format("answer", SCHEMA),
        )

        kwargs = client.chat.completions.create.call_args.kwargs
        # The schema degraded to JSON mode rather than being given up; the
        # other two had nothing weaker to fall back to.
        assert kwargs["response_format"] == {"type": "json_object"}
        assert "temperature" not in kwargs
        assert "reasoning_effort" not in kwargs

    def test_each_drop_is_logged_so_a_degraded_run_is_readable(self):
        client = _client(bad_request("Unsupported parameter: 'temperature'"))

        with patch("src.openai_call.logger") as log:
            _call(client, temperature=0)

        assert "temperature" in " ".join(str(c) for c in log.warning.call_args_list)


class TestErrorsThatAreNotArgumentRefusals:
    """Dropping arguments at a real error would hide it behind a worse reply."""

    def test_a_bad_request_naming_no_argument_is_raised(self):
        client = Mock()
        client.chat.completions.create.side_effect = bad_request(
            "The model `test-model` does not exist"
        )

        with pytest.raises(BadRequestError):
            _call(client, temperature=0)

        assert client.chat.completions.create.call_count == 1

    def test_a_bad_request_naming_an_argument_we_did_not_send_is_raised(self):
        client = Mock()
        client.chat.completions.create.side_effect = bad_request(
            "Unsupported parameter: 'temperature'"
        )

        with pytest.raises(BadRequestError):
            _call(client)

    def test_other_api_errors_pass_straight_through(self):
        """A bad key must not be retried into a request missing its schema."""
        client = Mock()
        client.chat.completions.create.side_effect = _http_error(
            401, "Incorrect API key provided", AuthenticationError
        )

        with pytest.raises(AuthenticationError):
            _call(client, temperature=0)

    def test_a_model_that_refuses_everything_terminates(self):
        """Bounded by the arguments there are to give up, so no infinite loop."""
        client = Mock()
        client.chat.completions.create.side_effect = bad_request(
            "Unsupported parameter: 'temperature'"
        )

        with pytest.raises(BadRequestError):
            _call(client, temperature=0)


class TestJsonSchemaFormat:
    def test_asks_for_strict_mode(self):
        fmt = json_schema_format("answer", SCHEMA)
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"] == {
            "name": "answer",
            "strict": True,
            "schema": SCHEMA,
        }


class TestReplyText:
    def test_returns_the_content_and_finish_reason(self):
        assert reply_text(_ok_response(" hi ", "stop")) == ("hi", "stop")

    def test_an_empty_reply_keeps_its_finish_reason(self):
        """"length" with no content is a reasoning model that spent its
        ceiling before writing anything — worth telling apart from a bad answer."""
        assert reply_text(_ok_response(None, "length")) == ("", "length")

    def test_a_response_with_no_choices_is_empty_rather_than_an_error(self):
        response = Mock()
        response.choices = []
        assert reply_text(response) == ("", None)


class TestTheWorstCase:
    """Every argument refused in turn still has to reach a request that works.

    The attempt bound was one short of this: a strict schema costs two steps,
    not one, because it degrades to JSON mode before it is given up.
    """

    def test_every_argument_refused_in_turn_still_lands_a_call(self):
        client = _client(
            bad_request("Unsupported parameter: 'response_format.json_schema'"),
            bad_request("Unsupported parameter: 'response_format'"),
            bad_request("Unsupported parameter: 'temperature'"),
            bad_request("Unrecognized request argument supplied: reasoning_effort"),
            bad_request("Unsupported parameter: 'max_completion_tokens'"),
        )

        _call(
            client,
            temperature=0,
            reasoning_effort="low",
            response_format=json_schema_format("answer", SCHEMA),
        )

        kwargs = client.chat.completions.create.call_args.kwargs
        assert set(kwargs) == {"model", "messages", "max_tokens"}
        assert client.chat.completions.create.call_count == 6

    def test_the_bound_allows_that_many_attempts(self):
        assert _MAX_ATTEMPTS >= 6
