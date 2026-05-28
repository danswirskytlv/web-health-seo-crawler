"""
prompts.py
==========

Prompt templates for the AI Assistant.

Kept in a separate module so that improving the prompt — which we'll do
many times — doesn't require touching the calling code or the UI.

We use a structured prompt that asks Gemini to return JSON. That makes
the response parseable and the UI rendering deterministic: a missing
field becomes an obvious empty section, not a vague paragraph.
"""

from __future__ import annotations

# --- System / role description -------------------------------------------

SYSTEM_INSTRUCTION = """\
You are an assistant inside a Web Health and SEO diagnostic tool.

The user is typically a small business owner or a marketer — NOT a developer.
Your job is to explain a detected website issue in plain language and give
them a practical, copy-paste fix.

Rules:
- Speak in clear, everyday English. Avoid jargon. If you must use a term,
  explain it in the same sentence.
- Be concrete. Don't say "improve the title"; give a specific title.
- Keep each section short — 1 to 3 sentences.
- When a code snippet is appropriate (HTML tags, meta tags, image alt
  text), include it. If the issue isn't fixable with a snippet (e.g. slow
  response time), set code_snippet to an empty string.
- ALWAYS respond with a single valid JSON object matching the schema
  below. No surrounding markdown, no commentary, no code fences.
"""


# --- Output schema -------------------------------------------------------

RESPONSE_SCHEMA = """\
{
  "simple_explanation": "1-2 sentence plain-language explanation of what the issue is.",
  "why_it_matters":     "1-2 sentences on the impact on users and/or search rankings.",
  "suggested_fix":      "1-3 sentences describing the concrete fix to apply.",
  "code_snippet":       "HTML/code to paste, OR empty string if not applicable."
}
"""


# --- The actual prompt template ------------------------------------------

USER_PROMPT_TEMPLATE = """\
A web crawler detected the following issue:

- URL:         {url}
- Issue type:  {issue_type}
- Severity:    {severity}
- Description: {description}
- Recommended action: {recommendation}

Page context (best-effort, may be empty if we couldn't extract it):
- Current title:            {title}
- Current H1:               {h1}
- Current meta description: {meta_description}

Respond with a single JSON object that exactly matches this schema:

{schema}

Important:
- Return ONLY the JSON object. No markdown, no code fences, no commentary
  outside the JSON.
- Use double quotes for all keys and string values.
- Keep the code_snippet field short and ready to paste into an HTML file.
"""


def build_user_prompt(
    *,
    url: str,
    issue_type: str,
    severity: str,
    description: str,
    recommendation: str,
    title: str = "",
    h1: str = "",
    meta_description: str = "",
) -> str:
    """Fill in the prompt template with details of one specific issue."""
    return USER_PROMPT_TEMPLATE.format(
        url=url,
        issue_type=issue_type,
        severity=severity,
        description=description,
        recommendation=recommendation,
        title=title or "(not detected)",
        h1=h1 or "(not detected)",
        meta_description=meta_description or "(not detected)",
        schema=RESPONSE_SCHEMA,
    )
