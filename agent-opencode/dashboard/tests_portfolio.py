from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import Portfolio, Position, Share, Transaction


class PortfolioTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="test")
        self.client.force_authenticate(user=self.user)
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=150.0,
        )

    def test_create_portfolio(self):
        response = self.client.post("/api/v1/portfolios/", {"name": "My Portfolio"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 1)

    def test_buy_shares(self):
        portfolio = Portfolio.objects.create(user=self.user, name="P")
        response = self.client.post(
            f"/api/v1/portfolios/{portfolio.id}/buy/",
            {"share_id": self.share.id, "quantity": "10", "price": "100"},
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        position = Position.objects.get(portfolio=portfolio, share=self.share)
        self.assertEqual(position.quantity, Decimal("10"))
        self.assertEqual(Transaction.objects.filter(portfolio=portfolio, transaction_type=Transaction.BUY).count(), 1)

    def test_sell_shares(self):
        portfolio = Portfolio.objects.create(user=self.user, name="P")
        self.client.post(
            f"/api/v1/portfolios/{portfolio.id}/buy/",
            {"share_id": self.share.id, "quantity": "10", "price": "100"},
            format="json",
        )
        response = self.client.post(
            f"/api/v1/portfolios/{portfolio.id}/sell/",
            {"share_id": self.share.id, "quantity": "3", "price": "120"},
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        position = Position.objects.get(portfolio=portfolio, share=self.share)
        self.assertEqual(position.quantity, Decimal("7"))
        self.assertEqual(Transaction.objects.filter(portfolio=portfolio, transaction_type=Transaction.SELL).count(), 1)

    def test_portfolio_value_and_pl(self):
        portfolio = Portfolio.objects.create(user=self.user, name="P")
        self.client.post(
            f"/api/v1/portfolios/{portfolio.id}/buy/",
            {"share_id": self.share.id, "quantity": "10", "price": "100"},
            format="json",
        )
        response = self.client.get(f"/api/v1/portfolios/{portfolio.id}/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("total_cost_basis", data)
        self.assertIn("total_current_value", data)
        self.assertIn("total_unrealized_pl", data)

    def test_sell_more_than_have(self):
        portfolio = Portfolio.objects.create(user=self.user, name="P")
        self.client.post(
            f"/api/v1/portfolios/{portfolio.id}/buy/",
            {"share_id": self.share.id, "quantity": "5", "price": "100"},
            format="json",
        )
        response = self.client.post(
            f"/api/v1/portfolios/{portfolio.id}/sell/",
            {"share_id": self.share.id, "quantity": "10", "price": "120"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
