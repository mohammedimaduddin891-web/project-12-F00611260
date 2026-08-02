#!/usr/bin/env python3
"""Project 12 donor thank-you assistant.

The service accepts synthetic donor records only, calls a project-scoped
OpenAI API key, and returns the generated letter plus token-usage evidence.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from openai import OpenAI


load_dotenv()

MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.4-mini-2026-03-17",
)

MAX_COMPLETION_TOKENS = int(
    os.getenv("MAX_COMPLETION_TOKENS", "150")
)

APP_PORT = int(
    os.getenv("APP_PORT", "8012")
)

ALLOCATION = {
    "project": os.getenv(
        "COST_PROJECT",
        "project12",
    ),
    "env": os.getenv(
        "COST_ENV",
        "lab",
    ),
    "team": os.getenv(
        "COST_TEAM",
        "it",
    ),
    "workload": os.getenv(
        "COST_WORKLOAD",
        "donor-thank-you",
    ),
}

api_key = os.getenv(
    "OPENAI_API_KEY",
    "",
).strip()

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not set"
    )

client = OpenAI(
    api_key=api_key
)

app = Flask(__name__)

SYSTEM_PROMPT = """
You draft donor thank-you letters for Grace & Mercy Relief.

All records are fictional and marked synthetic.

Write a warm, professional letter of no more than 120 words.
Mention the relief area and gift amount.
Do not invent tax or legal claims.
Do not add contact details that were not provided.

Return only the letter text.
""".strip()


def usage_to_dict(
    usage: Any,
) -> dict[str, int]:
    """Convert the OpenAI usage object into integer evidence."""

    if usage is None:
        return {
            "prompt_tokens": 0,
            "cached_input_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }

    prompt_details = getattr(
        usage,
        "prompt_tokens_details",
        None,
    )

    completion_details = getattr(
        usage,
        "completion_tokens_details",
        None,
    )

    return {
        "prompt_tokens": int(
            getattr(
                usage,
                "prompt_tokens",
                0,
            )
            or 0
        ),
        "cached_input_tokens": int(
            getattr(
                prompt_details,
                "cached_tokens",
                0,
            )
            or 0
        ),
        "completion_tokens": int(
            getattr(
                usage,
                "completion_tokens",
                0,
            )
            or 0
        ),
        "reasoning_tokens": int(
            getattr(
                completion_details,
                "reasoning_tokens",
                0,
            )
            or 0
        ),
        "total_tokens": int(
            getattr(
                usage,
                "total_tokens",
                0,
            )
            or 0
        ),
    }


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "model": MODEL,
            "max_completion_tokens": (
                MAX_COMPLETION_TOKENS
            ),
            "allocation": ALLOCATION,
        }
    )


@app.post("/draft")
def draft_letter():
    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )

    required = [
        "donor_id",
        "first_name",
        "gift_amount",
        "relief_area",
    ]

    missing = [
        field
        for field in required
        if field not in payload
    ]

    if missing:
        return (
            jsonify(
                {
                    "error": (
                        "missing required fields: "
                        + ", ".join(missing)
                    )
                }
            ),
            400,
        )

    donor_id = str(
        payload["donor_id"]
    ).strip()

    if not donor_id.startswith(
        "SYN-"
    ):
        return (
            jsonify(
                {
                    "error": (
                        "only synthetic donor IDs "
                        "beginning with SYN- are allowed"
                    )
                }
            ),
            400,
        )

    try:
        gift_amount = float(
            payload["gift_amount"]
        )
    except (
        TypeError,
        ValueError,
    ):
        return (
            jsonify(
                {
                    "error": (
                        "gift_amount must be numeric"
                    )
                }
            ),
            400,
        )

    if gift_amount <= 0:
        return (
            jsonify(
                {
                    "error": (
                        "gift_amount must be "
                        "greater than zero"
                    )
                }
            ),
            400,
        )

    first_name = str(
        payload["first_name"]
    ).strip()[:60]

    relief_area = str(
        payload["relief_area"]
    ).strip()[:160]

    channel = str(
        payload.get(
            "channel",
            "email",
        )
    ).strip()[:30]

    user_prompt = f"""
Synthetic donor record:

Donor ID: {donor_id}
First name: {first_name}
Gift amount: ${gift_amount:,.2f}
Relief area: {relief_area}
Delivery channel: {channel}

Draft the thank-you letter now.
""".strip()

    try:
        response = (
            client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                max_completion_tokens=(
                    MAX_COMPLETION_TOKENS
                ),
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
            or ""
        )

        return jsonify(
            {
                "status": "ok",
                "donor_id": donor_id,
                "letter": content.strip(),
                "model": response.model,
                "provider_request_id": getattr(
                    response,
                    "_request_id",
                    None,
                ),
                "usage": usage_to_dict(
                    response.usage
                ),
                "allocation": ALLOCATION,
            }
        )

    except Exception as exc:
        app.logger.exception(
            "OpenAI request failed"
        )

        return (
            jsonify(
                {
                    "status": "error",
                    "error_type": (
                        type(exc).__name__
                    ),
                    "message": str(exc)[:300],
                }
            ),
            502,
        )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=APP_PORT,
    )
