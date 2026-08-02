#!/usr/bin/env python3
"""token_cost.py — Predict a serverless model-API bill before it bites.

Per-token model APIs bill input and output tokens SEPARATELY, per 1M tokens.
Output tokens typically cost 4-8x input. One request is nothing; a million
requests a month is a five-figure line item. Always project to volume.

All prices here are MID-2026 SNAPSHOTS and WILL have drifted. Re-verify against
the live vendor console before committing money against any number.

Usage:
  python3 token_cost.py --in 1000 --out 500 --in-price 5 --out-price 25
  python3 token_cost.py --in 1000 --out 500 --in-price 5 --out-price 25 --requests 1000000
  python3 token_cost.py --in 1000 --out 500 --tier opus48 --requests 1000000
"""
import argparse

# (input $/1M, output $/1M) -- mid-2026 snapshots; re-verify at the console.
TIERS = {
    "gpt55":      (5.00, 30.00),
    "gpt55pro":   (30.00, 180.00),
    "gpt54":      (2.50, 15.00),
    "gpt54mini":  (0.75, 4.50),
    "gpt54nano":  (0.20, 1.25),
    "opus48":     (5.00, 25.00),
    "sonnet46":   (3.00, 15.00),
    "haiku45":    (1.00, 5.00),
    "gemini3pro": (2.00, 12.00),
    "gemini3flash": (0.50, 3.00),
}


def cost(in_tok, out_tok, in_price, out_price):
    return (in_tok / 1e6) * in_price + (out_tok / 1e6) * out_price


def main():
    p = argparse.ArgumentParser(description="Predict a per-token model-API bill.")
    p.add_argument("--in", dest="in_tok", type=int, required=True, help="input tokens/request")
    p.add_argument("--out", dest="out_tok", type=int, required=True, help="output tokens/request")
    p.add_argument("--in-price", type=float, help="$ per 1M input tokens")
    p.add_argument("--out-price", type=float, help="$ per 1M output tokens")
    p.add_argument("--tier", choices=sorted(TIERS), help="use a built-in price snapshot")
    p.add_argument("--requests", type=int, default=1, help="number of requests (e.g. monthly volume)")
    a = p.parse_args()

    if a.tier:
        in_price, out_price = TIERS[a.tier]
    elif a.in_price is not None and a.out_price is not None:
        in_price, out_price = a.in_price, a.out_price
    else:
        p.error("provide --tier OR both --in-price and --out-price")

    per_req = cost(a.in_tok, a.out_tok, in_price, out_price)
    total = per_req * a.requests
    ratio = out_price / in_price if in_price else float("inf")

    print(f"price snapshot : ${in_price}/1M in, ${out_price}/1M out  (output is {ratio:.1f}x input)")
    print(f"per request    : ${per_req:.6f}")
    if a.requests > 1:
        print(f"x {a.requests:,} requests : ${total:,.2f}")
    print("NOTE: mid-2026 snapshot prices -- re-verify at the live console.")


if __name__ == "__main__":
    main()
