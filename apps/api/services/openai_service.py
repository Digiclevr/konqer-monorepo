"""
OpenAI Service - GPT-4o integration for all 12 services
"""
from openai import AsyncOpenAI
from typing import Dict, Any, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate_cold_dm(
        self,
        context: Dict[str, Any],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate personalized cold LinkedIn DM

        Args:
            context: {
                "name": "John Doe",
                "title": "VP Sales",
                "company": "Acme Corp",
                "company_size": 250,
                "tech_stack": ["Salesforce", "HubSpot"],
                "recent_activity": [...],
                "interests": [...]
            }
        """
        prompt = self._build_cold_dm_prompt(context)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """You are a world-class B2B sales expert specializing in cold outreach.
Your messages are concise (max 150 words), highly personalized, and focus on value.
You always reference specific details about the prospect's work or company.
You never use generic templates or salesy language."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=300
        )

        message = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return {
            "message": message,
            "tokens_used": tokens_used,
            "model": self.model
        }

    async def generate_objection_response(
        self,
        objection: str,
        context: Dict[str, Any],
        framework: str
    ) -> Dict[str, Any]:
        """
        Generate sales objection handling response

        Args:
            objection: "It's too expensive for us right now"
            context: {
                "deal_size": 50000,
                "industry": "SaaS",
                "competitor": "HubSpot",
                "pain_points": ["manual data entry", "low conversion"]
            }
            framework: "Cost vs Value" or "Urgency Creation"
        """
        prompt = f"""Generate a sales objection handling response using the {framework} framework.

**Objection:** "{objection}"

**Context:**
- Deal Size: ${context['deal_size']:,}
- Industry: {context['industry']}
- Competing with: {context.get('competitor', 'N/A')}
- Pain Points: {', '.join(context['pain_points'])}

**Response Structure:**
1. Empathy (acknowledge concern)
2. Reframe (shift perspective)
3. Evidence (data, case study, ROI calc)
4. Action (next step)

Generate the response (200-250 words):"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a sales objection handling expert. Your responses follow proven sales frameworks and focus on value demonstration."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.6,
            max_tokens=400
        )

        return {
            "response": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "framework_used": framework
        }

    async def generate_carousel(
        self,
        topic: str,
        target_audience: str,
        slides_count: int = 10
    ) -> Dict[str, Any]:
        """
        Generate LinkedIn carousel structure
        """
        prompt = f"""Create a {slides_count}-slide LinkedIn carousel about: {topic}

Target Audience: {target_audience}

For each slide, provide:
1. Title (max 8 words)
2. Content (max 50 words)
3. Visual suggestion (brief description for design)

Format as JSON array:
[
  {{"slide": 1, "title": "...", "content": "...", "visual": "..."}},
  ...
]

Make it engaging, actionable, and viral-worthy."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a LinkedIn viral content expert. Create carousel structures that maximize engagement."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=1500
        )

        return {
            "carousel_structure": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens
        }

    async def generate_generic(
        self,
        service: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generic generation endpoint for other services
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            "output": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "model": self.model
        }

    def _build_cold_dm_prompt(self, context: Dict[str, Any]) -> str:
        """Build detailed prompt for cold DM generation"""
        recent_activity = "\n".join(
            f"- {post.get('summary', '')}"
            for post in context.get('recent_activity', [])[:3]
        )

        return f"""Generate a cold LinkedIn DM for:

**Target Profile:**
- Name: {context['name']}
- Title: {context['title']}
- Company: {context['company']} ({context.get('company_size', 'unknown')} employees)
- Tech Stack: {', '.join(context.get('tech_stack', [])[:5])}

**Recent Activity:**
{recent_activity or 'No recent activity available'}

**Interests:** {', '.join(context.get('interests', []))}

**Your Task:**
Write a personalized cold DM that:
1. References ONE specific detail from their recent activity or tech stack
2. Offers concrete value related to their role
3. Ends with a soft CTA (question or meeting proposal)
4. Is 100-150 words maximum
5. Sounds human, not salesy

Generate the message now:"""
