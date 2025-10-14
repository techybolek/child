"""Location search handler for childcare facility search queries"""

from .base import BaseHandler
from ..prompts import LOCATION_SEARCH_TEMPLATE


class LocationSearchHandler(BaseHandler):
    """Handles queries about finding childcare facilities near a location"""

    def handle(self, query: str) -> dict:
        """Return template response with link to Texas HHS childcare search"""

        return {
            'answer': LOCATION_SEARCH_TEMPLATE,
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
