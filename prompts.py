"""Prompt templates, platform rules and tone settings."""

# Rules for each platform. They are added to the prompt and checked after generation.
PLATFORMS = {
    "linkedin": {
        "max_chars": 1300,
        "style": "professional and insightful, short paragraphs, focus on value and results",
        "hashtags": "3 to 5 relevant professional hashtags",
    },
    "instagram": {
        "max_chars": 2200,
        "style": "casual, visual and energetic, use a few emojis, start with a strong hook",
        "hashtags": "8 to 12 popular and niche hashtags",
    },
    "email": {
        "max_chars": 1500,
        "style": "clear and personal, greeting, 2-3 short paragraphs, sign-off",
        "hashtags": "no hashtags (return an empty list)",
    },
    "twitter": {
        "max_chars": 280,
        "style": "punchy and concise, one idea only",
        "hashtags": "1 or 2 hashtags",
    },
}

# Each tone has a default temperature and top_p.
# Low temperature = consistent and factual. High temperature = creative and surprising.
TONES = {
    "professional": {"temperature": 0.3, "top_p": 0.8, "guide": "confident, clear and trustworthy"},
    "friendly": {"temperature": 0.6, "top_p": 0.9, "guide": "warm, simple and approachable"},
    "witty": {"temperature": 0.9, "top_p": 0.95, "guide": "clever, playful, with light humor"},
    "luxury": {"temperature": 0.5, "top_p": 0.85, "guide": "elegant, exclusive and refined"},
    "urgent": {"temperature": 0.5, "top_p": 0.9, "guide": "exciting, time-limited, action-driven"},
}

SYSTEM_INSTRUCTION = (
    "You are a senior marketing copywriter. "
    "Only use facts from the product description. Never invent prices, discounts or features. "
    "Always respect the platform's length limit."
)

MASTER_TEMPLATE = """Write marketing copy for the product below.

PRODUCT: {product_name}
DESCRIPTION: {description}
TARGET AUDIENCE: {audience}

PLATFORM: {platform_label}
- Style: {style}
- Hashtags: {hashtags}
- The headline + body + call to action together must stay under {max_chars} characters.

TONE: {tone} ({tone_guide})
{email_rule}
Return the result as JSON matching the requested schema."""


def build_prompt(request):
    """Fill the master template with the user's variables (dynamic f-string compilation)."""
    platform = PLATFORMS[request.platform]
    tone = TONES[request.tone]
    email_rule = "- Include a short, catchy subject_line.\n" if request.platform == "email" else ""

    return MASTER_TEMPLATE.format(
        product_name=request.product_name.strip(),
        description=request.description.strip(),
        audience=request.audience.strip(),
        platform_label=request.platform.capitalize(),
        style=platform["style"],
        hashtags=platform["hashtags"],
        max_chars=platform["max_chars"],
        tone=request.tone,
        tone_guide=tone["guide"],
        email_rule=email_rule,
    )
