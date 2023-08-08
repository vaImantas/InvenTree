"""Unit tests for label API"""

from django.urls import reverse

from InvenTree.unit_test import InvenTreeAPITestCase


class TestReportTests(InvenTreeAPITestCase):
    """Tests for the StockItem TestReport templates."""

    fixtures = [
        'category',
        'part',
        'location',
        'stock',
    ]

    roles = [
        'stock.view',
        'stock_location.view',
    ]

    list_url = reverse('api-stockitem-testreport-list')

    def do_list(self, filters=None):
        """Helper function to request list of labels with provided filters"""
        # Set default - see B006
        if filters is None:
            filters = {}

        response = self.client.get(self.list_url, filters, format='json')

        self.assertEqual(response.status_code, 200)

        return response.data

    def test_list(self):
        """Test the API list endpoint"""
        response = self.do_list()

        # TODO - Add some report templates to the fixtures
        self.assertEqual(len(response), 0)

        # TODO - Add some tests to this response
        response = self.do_list(
            {
                'item': 10,
            }
        )

        # TODO - Add some tests to this response
        response = self.do_list(
            {
                'item': 100000,
            }
        )

        # TODO - Add some tests to this response
        response = self.do_list(
            {
                'items': [10, 11, 12],
            }
        )
