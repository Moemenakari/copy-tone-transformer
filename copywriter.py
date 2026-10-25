"""
Automated Copywriting & Tone Transformer

Takes a product description and generates marketing copy for several
platforms at once, in the tone you choose, using the Gemini API.

Examples:
  python copywriter.py --product "EcoBottle" --description "Steel bottle, keeps drinks cold 24h" --platform all --tone witty
  python copywriter.py --csv sample_products.csv --tone professional
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_random_exponential

from models import CopyRequest, CopyResult, MarketingCopy
from prompts import PLATFORMS, SYSTEM_INSTRUCTION, TONES, build_prompt

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_CONCURRENT = 3  # how many requests can run at the same time
OUTPUT_DIR = Path("outputs")


def resolve_settings(tone, temperature=None, top_p=None):
    """Use the tone's default values unless the user overrides them."""
    defaults = TONES[tone]
    temp = defaults["temperature"] if temperature is None else temperature
    top = defaults["top_p"] if top_p is None else top_p
    if not 0.0 <= temp <= 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")
    if not 0.0 < top <= 1.0:
        raise ValueError("top_p must be between 0.0 and 1.0")
    return temp, top


def measure(copy, platform):
    """Count the characters the reader will see and check the platform limit."""
    text = f"{copy.headline}\n\n{copy.body}\n\n{copy.call_to_action}"
    if copy.hashtags:
        text += "\n\n" + " ".join(copy.hashtags)
    count = len(text)
    return count, count <= PLATFORMS[platform]["max_chars"]


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(4), reraise=True)
async def call_model(client, prompt, temperature, top_p):
    """One API call. Retries with exponential backoff + jitter (e.g. on 429 rate limits)."""
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=1024,
            response_mime_type="application/json",
            response_schema=MarketingCopy,
        ),
    )
    return MarketingCopy.model_validate_json(response.text)


async def generate_copy(client, request, semaphore, temperature=None, top_p=None):
    temp, top = resolve_settings(request.tone, temperature, top_p)
    prompt = build_prompt(request)

    async with semaphore:  # limits how many calls run in parallel
        copy = await call_model(client, prompt, temp, top)

    count, ok = measure(copy, request.platform)
    return CopyResult(
        platform=request.platform,
        tone=request.tone,
        temperature=temp,
        top_p=top,
        copy_text=copy,
        char_count=count,
        within_limit=ok,
    )


async def run_batch(client, requests, temperature=None, top_p=None):
    """Run all requests concurrently. One failure doesn't stop the others."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [generate_copy(client, r, semaphore, temperature, top_p) for r in requests]
    return await asyncio.gather(*tasks, return_exceptions=True)


def load_csv(path, tone, audience):
    """Each CSV row: product_name, description, platform (optional: tone)."""
    requests = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            platforms = expand_platforms(row.get("platform") or "all")
            for p in platforms:
                requests.append(CopyRequest(
                    product_name=row["product_name"],
                    description=row["description"],
                    platform=p,
                    tone=(row.get("tone") or tone).lower(),
                    audience=row.get("audience") or audience,
                ))
    return requests


def expand_platforms(value):
    value = value.lower().strip()
    if value == "all":
        return ["linkedin", "instagram", "email"]
    return [p.strip() for p in value.split(",") if p.strip()]


def print_result(product, result):
    c = result.copy_text
    limit = PLATFORMS[result.platform]["max_chars"]
    status = "OK" if result.within_limit else "OVER LIMIT"
    print("\n" + "=" * 60)
    print(f" {product} | {result.platform.upper()} | tone: {result.tone} "
          f"| temp={result.temperature} top_p={result.top_p}")
    print("=" * 60)
    if c.subject_line:
        print(f"Subject: {c.subject_line}\n")
    print(c.headline + "\n")
    print(c.body + "\n")
    print(c.call_to_action)
    if c.hashtags:
        print("\n" + " ".join(c.hashtags))
    print(f"\n[{result.char_count}/{limit} chars - {status}]")


def save_results(items):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"copy_{datetime.now():%Y%m%d_%H%M%S}.json"
    data = [{"product": product, **result.model_dump()} for product, result in items]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate platform-specific marketing copy with AI.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--product", help="Product name")
    source.add_argument("--csv", help="CSV file with many products (bulk mode)")
    parser.add_argument("--description", help="Raw product description")
    parser.add_argument("--platform", default="all",
                        help="linkedin, instagram, email, twitter, a comma list, or 'all'")
    parser.add_argument("--tone", default="professional", choices=list(TONES))
    parser.add_argument("--audience", default="general audience")
    parser.add_argument("--temperature", type=float, help="Override tone default (0.0-2.0)")
    parser.add_argument("--top-p", type=float, dest="top_p", help="Override tone default (0.0-1.0)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to outputs/")
    args = parser.parse_args(argv)

    if args.product and not args.description:
        parser.error("--description is required with --product")
    for p in expand_platforms(args.platform):
        if p not in PLATFORMS:
            parser.error(f"unknown platform '{p}'. Choose from: {', '.join(PLATFORMS)} or all")
    try:
        resolve_settings(args.tone, args.temperature, args.top_p)
    except ValueError as error:
        parser.error(str(error))
    return args


def main(argv=None):
    args = parse_args(argv)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Missing GEMINI_API_KEY. Copy .env.example to .env and add your key.")
        sys.exit(1)

    if args.csv:
        requests = load_csv(args.csv, args.tone, args.audience)
    else:
        requests = [
            CopyRequest(product_name=args.product, description=args.description,
                        platform=p, tone=args.tone, audience=args.audience)
            for p in expand_platforms(args.platform)
        ]

    print(f"Generating {len(requests)} piece(s) of copy with {MODEL}...")
    client = genai.Client(api_key=api_key)
    results = asyncio.run(run_batch(client, requests, args.temperature, args.top_p))

    saved = []
    for request, result in zip(requests, results):
        if isinstance(result, Exception):
            print(f"\n[Error] {request.product_name} / {request.platform}: {result}")
            continue
        print_result(request.product_name, result)
        saved.append((request.product_name, result))

    if saved and not args.no_save:
        print(f"\nSaved to {save_results(saved)}")


if __name__ == "__main__":
    main()
