"""
Apollo.io Service - Contact enrichment
"""
import httpx
from typing import Dict, Any, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class ApolloService:
    def __init__(self):
        self.api_key = settings.APOLLO_API_KEY
        self.base_url = settings.APOLLO_BASE_URL

    async def enrich_profile(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich contact profile using Apollo.io API

        Args:
            context: {
                "name": "John Doe",
                "company": "Acme Corp",
                "linkedin_url": "https://linkedin.com/in/johndoe" (optional)
            }

        Returns:
            Enriched context with:
            - email
            - phone
            - company_size
            - tech_stack
            - title (verified)
            - etc.
        """
        # If no Apollo API key, return original context
        if not self.api_key:
            logger.warning("Apollo API key not configured, returning original context")
            return context

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Enrich person
                person_data = await self._enrich_person(
                    client,
                    name=context.get("name"),
                    company=context.get("company"),
                    linkedin_url=context.get("linkedin_url")
                )

                if person_data:
                    # Merge enriched data
                    context.update({
                        "email": person_data.get("email"),
                        "phone": person_data.get("phone_numbers", [None])[0],
                        "title": person_data.get("title") or context.get("title"),
                        "linkedin_url": person_data.get("linkedin_url") or context.get("linkedin_url")
                    })

                    # Enrich organization
                    if person_data.get("organization"):
                        org = person_data["organization"]
                        context.update({
                            "company": org.get("name") or context.get("company"),
                            "company_size": org.get("estimated_num_employees"),
                            "tech_stack": org.get("technologies", []),
                            "industry": org.get("industry")
                        })

                return context

        except httpx.RequestError as e:
            logger.error(f"Apollo API request error: {e}")
            return context
        except Exception as e:
            logger.error(f"Apollo enrichment error: {e}")
            return context

    async def _enrich_person(
        self,
        client: httpx.AsyncClient,
        name: Optional[str] = None,
        company: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call Apollo.io people enrichment API
        """
        if not name and not linkedin_url:
            return None

        url = f"{self.base_url}/people/match"

        params = {
            "api_key": self.api_key
        }

        data = {}

        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        else:
            if name:
                # Split name into first/last
                name_parts = name.split(maxsplit=1)
                data["first_name"] = name_parts[0]
                if len(name_parts) > 1:
                    data["last_name"] = name_parts[1]

            if company:
                data["organization_name"] = company

        if not data:
            return None

        try:
            response = await client.post(url, params=params, json=data)

            if response.status_code == 200:
                result = response.json()
                return result.get("person")
            else:
                logger.warning(f"Apollo API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Apollo people match error: {e}")
            return None

    async def search_people(
        self,
        query: Dict[str, Any],
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Search people using Apollo.io

        Args:
            query: {
                "person_titles": ["CEO", "Founder"],
                "organization_num_employees_ranges": ["1,10", "11,50"],
                "q_keywords": "SaaS"
            }
        """
        if not self.api_key:
            return {"people": [], "total": 0}

        url = f"{self.base_url}/mixed_people/search"

        params = {
            "api_key": self.api_key,
            "page": page,
            "per_page": per_page
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, params=params, json=query)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Apollo search error: {response.status_code}")
                    return {"people": [], "total": 0}

        except Exception as e:
            logger.error(f"Apollo search error: {e}")
            return {"people": [], "total": 0}
