from groq import Groq


class AiService:
    def __init__(self, api_key: str):
        self._client = Groq(api_key=api_key)

    def rewrite_text(self, original_text: str, rewrite_type: str) -> str:
        style_prompts = {
            "fix_grammar": (
                "You are a grammar expert. Fix grammatical errors, spelling mistakes, and punctuation issues. "
                "Keep the original tone and meaning. Return only the rewritten text."
            ),
            "make_pro": (
                "You are a professional business writer. Rewrite the text in a formal, concise, polished tone. "
                "Remove excessive punctuation, all caps, and emotional language. Return only the rewritten text."
            ),
            "make_announcement": (
                "You are a communications specialist. Rewrite the text as a clear, engaging announcement. "
                "Use a professional tone and remove urgency-based manipulation. Return only the rewritten text."
            ),
            "simplify": (
                "You are a clarity expert. Rewrite the text using simple, direct language and short sentences. "
                "Return only the rewritten text."
            ),
        }
        user_prompts = {
            "fix_grammar": f"Fix the grammar and spelling in this text:\n\n{original_text}",
            "make_pro": f"Make this text professional and business-appropriate:\n\n{original_text}",
            "make_announcement": f"Turn this into a clear, professional announcement:\n\n{original_text}",
            "simplify": f"Simplify this text for easy understanding:\n\n{original_text}",
        }

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": style_prompts.get(rewrite_type, style_prompts["fix_grammar"])},
                {"role": "user", "content": user_prompts.get(rewrite_type, user_prompts["fix_grammar"])},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("AI rewrite returned empty content")
        return content.strip()

    def chat_reply(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Quincy, a TON Communication Assistant for Telegram. "
                        "Help users communicate clearly, professionally, and safely in TON or Web3 contexts. "
                        "Keep replies short and action-oriented. "
                        "Do not invent wallet balances, transactions, or other real-time facts."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("AI chat returned empty content")
        return content.strip()
