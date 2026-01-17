import json
import logging
import os
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv

from ..exceptions import InvalidResponseError

# Load environment variables
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)

# Maximum number of retry attempts for postprocessing
MAX_POSTPROCESS_RETRIES = 5

# Valid JSON escape sequences
VALID_JSON_ESCAPES = {
    '\\"': '"',  # escaped quote
    "\\\\": "\\",  # escaped backslash
    "\\/": "/",  # escaped forward slash
    "\\n": "\n",  # newline
    "\\t": "\t",  # tab
    "\\r": "\r",  # carriage return
    "\\b": "\b",  # backspace
    "\\f": "\f",  # form feed
}


def _fix_invalid_escapes(json_str: str) -> str:
    """
    Fix invalid escape sequences in JSON strings.
    Escapes unescaped backslashes that are not part of valid escape sequences.
    Only processes content inside JSON string literals (between quotes).
    """
    result = []
    i = 0
    in_string = False

    while i < len(json_str):
        char = json_str[i]
        if char == '"':
            backslash_count = 0
            j = i - 1
            while j >= 0 and json_str[j] == "\\":
                backslash_count += 1
                j -= 1
            if backslash_count % 2 == 0:
                in_string = not in_string
                result.append(char)
            else:
                result.append(char)
        elif char == "\\" and in_string:
            if i + 1 < len(json_str):
                next_char = json_str[i + 1]
                escape_pair = f"\\{next_char}"

                if escape_pair in VALID_JSON_ESCAPES or (
                    next_char == "u" and i + 5 < len(json_str)
                ):
                    result.append(char)
                else:
                    result.append("\\\\")
            else:
                result.append("\\\\")
        else:
            result.append(char)

        i += 1

    return "".join(result)


def _clean_json_response(response: str) -> str:
    """Remove common JSON markdown formatting and extra text."""
    response = response.strip()
    # Remove markdown code blocks if present
    if response.startswith("```"):
        # Find the first newline to skip "json" or other language identifiers
        first_newline = response.find("\n")
        if first_newline != -1:
            response = response[first_newline + 1 :]
        # Remove trailing ``` if present
        if response.endswith("```"):
            response = response[:-3]

    return response.strip()


def _create_json_object(
    item: dict, include_ref: bool, extra_fields: dict | None = None
) -> dict:
    """Create standardized JSON object from item."""
    json_obj = {
        "question type": item["question type"],
        "question": item["question"],
        "answer": item["answer"],
    }
    if include_ref:
        json_obj["ref"] = item["ref"]
    if extra_fields:
        json_obj.update(extra_fields)
    return json_obj


# Mapping from config_key to expected question type
CONFIG_KEY_TO_QUESTION_TYPE = {
    "qa_fact_based": "Factual Question",
    "qa_multi_hop": "Multi-hop Reasoning Question",
    "qa_summary": "Summarization Question",
    "qa_multi_document_information_integration": "Multi-document Information Integration Question",
    "qa_multi_document_compare": "Multi-document Comparison Question",
}


def _fix_question_type(item: dict, expected_question_type: str | None) -> None:
    """
    Fix question type if it doesn't match the expected type.
    If expected_question_type is None, skip validation.
    """
    if expected_question_type is None:
        return

    current_type = item.get("question type", "").strip()

    # If already correct, return
    if current_type == expected_question_type:
        return

    # Log warning and fix
    logger.warning(
        f"Question type mismatch: expected '{expected_question_type}', "
        f"got '{current_type}'. Fixing automatically."
    )
    item["question type"] = expected_question_type


def _normalize_question_type(item: dict, has_ref: bool = True) -> None:
    """Normalize question type based on answer content and refs."""
    if has_ref:
        if "Unable to answer" in item["answer"] or item.get("ref") == []:
            item["question type"] = "Irrelevant Unsolvable Question"
            item["ref"] = []
    else:
        if "Unable to answer" in item["answer"]:
            item["question type"] = "Irrelevant Unsolvable Question"


def _retry_with_api(
    initial_response: str,
    client: Any,
    system_prompt: str,
    user_prompt: str,
    processor: Callable[[str], list | None],
    function_name: str,
) -> list:
    """Generic retry mechanism for postprocessing functions."""
    response = initial_response

    for retry_count in range(MAX_POSTPROCESS_RETRIES):
        try:
            result = processor(response)
            if result is not None:
                return result
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            logger.warning(
                f"{function_name} retry {retry_count + 1}/{MAX_POSTPROCESS_RETRIES}: {type(e).__name__}: {e}"
            )

        # Retry with new API call
        if retry_count < MAX_POSTPROCESS_RETRIES - 1:
            logger.info("Requesting new response from API...")
            response = client.generate(
                [{"system_prompt": system_prompt, "user_prompt": user_prompt}]
            )[0]

    raise InvalidResponseError(
        f"Failed to {function_name} after {MAX_POSTPROCESS_RETRIES} attempts"
    )


def postprocess(
    client: Any,
    response: str,
    system_prompt: str,
    user_prompt: str,
    expected_question_type: str | None = None,
) -> list:
    """
    Remove common extra characters in gpt-4o, check the question type and array format to avoid errors when saving as a JSON file.

    Args:
        client: API client
        response: LLM response string
        system_prompt: System prompt used
        user_prompt: User prompt used
        expected_question_type: Expected question type to validate against (e.g., "Factual Question")
    """

    def process_response(resp: str) -> list | None:
        resp = _clean_json_response(resp)
        try:
            response_data = json.loads(resp)
        except json.JSONDecodeError as e:
            # If JSON decode fails, try fixing escape sequences
            if "Invalid \\escape" in str(e) or "Invalid escape" in str(e):
                logger.debug("Attempting to fix invalid escape sequences...")
                resp = _fix_invalid_escapes(resp)
                response_data = json.loads(resp)
            else:
                raise

        output = []

        for item in response_data:
            has_ref = "ref" in item
            # Fix question type if it doesn't match expected
            _fix_question_type(item, expected_question_type)
            _normalize_question_type(item, has_ref)
            json_obj = _create_json_object(item, has_ref)
            output.append(json_obj)

        return output

    return _retry_with_api(
        response, client, system_prompt, user_prompt, process_response, "postprocess"
    )


def postprocess_irrelevant(
    client: Any,
    response: str,
    system_prompt: str,
    user_prompt: str,
    name: str,
) -> list:
    """
    Remove common extra characters in gpt-4o, check the question type and array format to avoid errors when saving as a JSON file.
    """

    def process_response(resp: str) -> list | None:
        resp = _clean_json_response(resp)
        # Fix invalid escape sequences before parsing
        try:
            response_data = json.loads(resp)
        except json.JSONDecodeError as e:
            # If JSON decode fails, try fixing escape sequences
            if "Invalid \\escape" in str(e) or "Invalid escape" in str(e):
                logger.debug("Attempting to fix invalid escape sequences...")
                resp = _fix_invalid_escapes(resp)
                response_data = json.loads(resp)
            else:
                raise

        output = []

        for item in response_data:
            _normalize_question_type(item, has_ref=True)
            json_obj = _create_json_object(item, True, {"paper_title": name})
            output.append(json_obj)

        return output

    return _retry_with_api(
        response,
        client,
        system_prompt,
        user_prompt,
        process_response,
        "postprocess_irrelevant",
    )
