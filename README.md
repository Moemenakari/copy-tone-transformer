# Copy & Tone Transformer — Automated Marketing Copywriter

**DecodeLabs Generative AI Internship — Project 2**

A Python command-line tool that turns a raw product description into ready-to-post marketing copy for **LinkedIn, Instagram, Email and Twitter/X** — in the tone you choose — using the Google Gemini API.

## How It Works
```
CLI / CSV input  →  Prompt compiler  →  Async Gemini calls  →  Validated JSON output
(product, tone,     (master template     (Semaphore + retry     (Pydantic model +
 platform)           + platform rules)    with backoff)          length check)
```

1. **Input** — product name, description, platform(s), tone and audience come from the CLI (`argparse`) or a CSV file for bulk jobs.
2. **Dynamic template** — the variables are injected into a hidden master template together with each platform's rules (style, hashtags, character limit).
3. **Inference parameters** — every tone has its own `temperature` and `top_p`:

   | Tone | Temperature | Top P | Result |
   |------|-------------|-------|--------|
   | professional | 0.3 | 0.80 | consistent, factual |
   | friendly | 0.6 | 0.90 | warm, natural |
   | luxury | 0.5 | 0.85 | elegant, refined |
   | urgent | 0.5 | 0.90 | action-driven |
   | witty | 0.9 | 0.95 | creative, surprising |

   Both can be overridden with `--temperature` and `--top-p`.
4. **Concurrency** — all platforms are generated at the same time with `asyncio.gather`, limited by an `asyncio.Semaphore` to avoid rate limits (HTTP 429).
5. **Resilience** — `tenacity` retries failed calls with randomized exponential backoff; one failed platform doesn't stop the rest.
6. **Structured output** — Gemini returns JSON that is validated with a Pydantic model (`headline`, `body`, `call_to_action`, `hashtags`, `subject_line`), then checked against the platform's character limit.

## Platform Rules
| Platform | Max chars | Style |
|----------|-----------|-------|
| LinkedIn | 1300 | professional, value-focused, 3–5 hashtags |
| Instagram | 2200 | energetic, emojis, 8–12 hashtags |
| Email | 1500 | personal, subject line, no hashtags |
| Twitter/X | 280 | punchy, 1–2 hashtags |

## Setup
```bash
git clone https://github.com/Moemenakari/copy-tone-transformer.git
cd copy-tone-transformer
pip install -r requirements.txt
```
Create a `.env` file (copy `.env.example`) and add your free key from [Google AI Studio](https://aistudio.google.com/apikey):
```
GEMINI_API_KEY=your_api_key_here
```

## Usage
**One product, all platforms:**
```bash
python copywriter.py --product "EcoBottle" --description "Steel bottle that keeps drinks cold for 24 hours" --platform all --tone witty
```

**Choose platforms and tune creativity:**
```bash
python copywriter.py --product "FocusDesk Lamp" --description "LED lamp with 5 brightness levels" --platform linkedin,twitter --tone professional --temperature 0.2
```

**Bulk mode from CSV:**
```bash
python copywriter.py --csv sample_products.csv
```

Results are printed and saved as JSON in the `outputs/` folder (use `--no-save` to skip).

## Tests
Tests use a fake async client, so no API key is needed:
```bash
python -m unittest test_copywriter.py
```

## Project Structure
```
copywriter.py        CLI, async pipeline, retry logic, output
prompts.py           master template, platform rules, tone settings
models.py            Pydantic models for input and output
sample_products.csv  example products for bulk mode
test_copywriter.py   unit tests
```

## Tech Stack
Python 3 · Google Gemini API (`google-genai`) · asyncio · Pydantic · Tenacity · argparse

## Author
**Mouemen Akkarie** — [GitHub](https://github.com/Moemenakari)
