import json
import time
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a professional email copywriter. Your job is to write personalized,
professional outreach emails.

Rules:
- Keep emails concise (150-250 words max)
- Use a professional but warm tone
- Personalize using the recipient's name, company, and any other provided details
- Include a clear call to action
- Do NOT use spammy language, excessive exclamation marks, or ALL CAPS
- Do NOT include placeholder text like [Your Name] — use the actual sender name provided
- Do NOT include a sign-off like "Best regards" or the sender's name at the end — this is added automatically
- End the email body with your last paragraph content only (no closing or signature)

You MUST respond with valid JSON in this exact format:
{"subject": "Email subject line here", "body": "Email body here"}

The body should be plain text with line breaks (use \\n for new lines).
Do not include any markdown formatting in the body."""


def generate_email(recipient, purpose=None):
    """Generate a personalized email for a recipient using OpenAI.

    Args:
        recipient: dict with keys like name, email, company, role, custom_note, etc.
        purpose: string describing the purpose/context of the email campaign.

    Returns:
        dict with 'subject' and 'body' keys.
    """
    purpose = purpose or config.EMAIL_PURPOSE

    # Build recipient context from all available fields
    recipient_info = "\n".join(
        f"- {key}: {value}"
        for key, value in recipient.items()
        if key != "email" and value
    )

    user_prompt = f"""Write a professional email for the following recipient:

{recipient_info}

SENDER INFORMATION (use this in the email, NOT placeholders):
- Sender Name: {config.SENDER_NAME}
- Sender Company: {config.COMPANY_NAME}

Purpose of this email: {purpose}

IMPORTANT: Use the actual sender name "{config.SENDER_NAME}" and company "{config.COMPANY_NAME}" in the email. Do NOT use placeholders like [Your Name] or [Your Company].

Respond with JSON only: {{"subject": "...", "body": "..."}}"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )
            content = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0].strip()

            result = json.loads(content)
            if "subject" in result and "body" in result:
                return result
            raise ValueError("Response missing 'subject' or 'body' keys")

        except Exception as e:
            if attempt < 2:
                print(f"  AI generation attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Failed to generate email after 3 attempts: {e}")
