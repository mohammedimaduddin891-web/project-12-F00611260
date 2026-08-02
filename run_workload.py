#!/usr/bin/env python3
"""Drive a fixed synthetic workload through the Project 12 API."""

from __future__ import annotations

import argparse
import json
import os
import time

from datetime import (
    datetime,
    timezone,
)
from itertools import cycle
from pathlib import Path

import requests

from dotenv import load_dotenv


load_dotenv()


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--requests",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--url",
        default=(
            "http://127.0.0.1:8012/draft"
        ),
    )

    parser.add_argument(
        "--donors",
        default="synthetic_donors.json",
    )

    parser.add_argument(
        "--output-dir",
        default="output",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.requests <= 0:
        raise SystemExit(
            "--requests must be greater than zero"
        )

    donors = json.loads(
        Path(
            args.donors
        ).read_text(
            encoding="utf-8"
        )
    )

    if (
        not isinstance(
            donors,
            list,
        )
        or not donors
    ):
        raise SystemExit(
            "synthetic_donors.json must contain "
            "a non-empty JSON list"
        )

    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    detail_path = (
        output_dir
        / "workload_requests.jsonl"
    )

    summary_path = (
        output_dir
        / "workload_summary.json"
    )

    input_price = float(
        os.getenv(
            "INPUT_PRICE_PER_MILLION",
            "0.75",
        )
    )

    cached_price = float(
        os.getenv(
            "CACHED_INPUT_PRICE_PER_MILLION",
            "0.075",
        )
    )

    output_price = float(
        os.getenv(
            "OUTPUT_PRICE_PER_MILLION",
            "4.50",
        )
    )

    totals = {
        "prompt_tokens": 0,
        "cached_input_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }

    succeeded = 0
    failed = 0
    started_at = utc_now()
    donor_stream = cycle(donors)

    with detail_path.open(
        "w",
        encoding="utf-8",
    ) as log_file:

        for index in range(
            1,
            args.requests + 1,
        ):
            donor = next(
                donor_stream
            )

            record = {
                "sequence": index,
                "timestamp_utc": utc_now(),
                "donor_id": donor.get(
                    "donor_id"
                ),
            }

            try:
                response = requests.post(
                    args.url,
                    json=donor,
                    timeout=180,
                )

                record["http_status"] = (
                    response.status_code
                )

                data = response.json()
                record["response"] = data

                if (
                    response.status_code == 200
                    and data.get("status")
                    == "ok"
                ):
                    succeeded += 1

                    usage = data.get(
                        "usage",
                        {},
                    )

                    for field in totals:
                        totals[field] += int(
                            usage.get(
                                field,
                                0,
                            )
                            or 0
                        )

                    print(
                        f"{index:03d}/"
                        f"{args.requests} "
                        "status=200 "
                        "total_tokens="
                        f"{usage.get('total_tokens', 0)} "
                        "request_id="
                        f"{data.get('provider_request_id')}"
                    )

                else:
                    failed += 1

                    print(
                        f"{index:03d}/"
                        f"{args.requests} "
                        f"status={response.status_code} "
                        "FAILED"
                    )

            except Exception as exc:
                failed += 1

                record["http_status"] = None

                record["error"] = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                print(
                    f"{index:03d}/"
                    f"{args.requests} "
                    f"request FAILED: {exc}"
                )

            log_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

            log_file.flush()

            if args.delay > 0:
                time.sleep(
                    args.delay
                )

    non_cached_tokens = max(
        totals["prompt_tokens"]
        - totals["cached_input_tokens"],
        0,
    )

    input_cost = (
        non_cached_tokens
        / 1_000_000
    ) * input_price

    cached_cost = (
        totals["cached_input_tokens"]
        / 1_000_000
    ) * cached_price

    output_cost = (
        totals["completion_tokens"]
        / 1_000_000
    ) * output_price

    usage_estimate = (
        input_cost
        + cached_cost
        + output_cost
    )

    summary = {
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "requested": args.requests,
        "succeeded": succeeded,
        "failed": failed,
        **totals,
        "pricing_usd_per_million": {
            "input": input_price,
            "cached_input": cached_price,
            "output": output_price,
        },
        "usage_estimated_cost_usd": round(
            usage_estimate,
            8,
        ),
        "detail_file": str(
            detail_path
        ),
    }

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\nWORKLOAD SUMMARY"
    )

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    if (
        failed == 0
        and succeeded
        == args.requests
    ):
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
