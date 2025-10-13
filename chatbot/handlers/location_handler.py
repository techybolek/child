"""Location search handler for childcare facility search queries"""

from .base import BaseHandler


class LocationSearchHandler(BaseHandler):
    """Handles queries about finding childcare facilities near a location"""

    def handle(self, query: str) -> dict:
        """Return template response with link to Texas HHS childcare search"""

        answer = """To search for childcare facilities near you, use the official Texas HHS Childcare Search tool:

**What you can do:**
- Search by address, city, or ZIP code
- Filter by facility type, age groups, and services
- View licensing status and inspection reports
- Check capacity and contact information

If you have questions about childcare assistance programs or eligibility, I'm here to help!"""

        return {
            'answer': answer,
            'sources': [],
            'response_type': 'location_search',
            'action_items': [
                {
                    'type': 'link',
                    'url': 'https://childcare.hhs.texas.gov/Public/ChildCareSearch',
                    'label': 'Search for Childcare Facilities',
                    'description': 'Official Texas HHS facility search tool'
                }
            ]
        }
