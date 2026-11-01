from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dashboard.models import Portfolio, Position, Transaction

from .portfolio_serializer import (
    PortfolioSerializer,
    PositionSerializer,
    TransactionSerializer,
)

QUANT = Decimal("0.000001")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(QUANT)


def _resolve_price(share, price):
    """Use the explicit price or the last known market price."""
    value = price if price is not None else share.last_price
    if value is None:
        raise ValueError(
            f"Цена {share.ticker} неизвестна: укажите price или обновите котировки"
        )
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Некорректная цена") from exc
    if value <= 0:
        raise ValueError("price must be positive")
    return _quantize(value)


class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user).prefetch_related(
            "positions__share", "transactions"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="buy")
    def buy(self, request, pk=None):
        portfolio = self.get_object()
        data = request.data.copy()
        if "transaction_type" not in data:
            data["transaction_type"] = Transaction.BUY
        serializer = TransactionSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        share = serializer.validated_data["share"]
        quantity = _quantize(Decimal(str(serializer.validated_data["quantity"])))
        try:
            price = _resolve_price(share, serializer.validated_data.get("price"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response(
                {"detail": "quantity must be positive"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            position, _ = Position.objects.select_for_update().get_or_create(
                portfolio=portfolio,
                share=share,
                defaults={"quantity": Decimal(0), "avg_buy_price": Decimal(0)},
            )
            position = Position.objects.select_for_update().get(id=position.id)

            total_cost_new = position.quantity * position.avg_buy_price + quantity * price
            new_quantity = position.quantity + quantity
            position.avg_buy_price = _quantize(total_cost_new / new_quantity)
            position.quantity = new_quantity
            position.save()

            trans = Transaction.objects.create(
                portfolio=portfolio,
                share=share,
                transaction_type=Transaction.BUY,
                quantity=quantity,
                price=price,
                total=_quantize(quantity * price),
            )

        return Response(
            {"status": "ok", "transaction_id": trans.id, "position_id": position.id},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="sell")
    def sell(self, request, pk=None):
        portfolio = self.get_object()
        data = request.data.copy()
        if "transaction_type" not in data:
            data["transaction_type"] = Transaction.SELL
        serializer = TransactionSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        share = serializer.validated_data["share"]
        quantity = _quantize(Decimal(str(serializer.validated_data["quantity"])))
        try:
            price = _resolve_price(share, serializer.validated_data.get("price"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response(
                {"detail": "quantity must be positive"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The row must be locked and checked inside the same transaction,
        # otherwise two concurrent sells can both pass the quantity check.
        with transaction.atomic():
            try:
                position = Position.objects.select_for_update().get(
                    portfolio=portfolio, share=share
                )
            except Position.DoesNotExist:
                return Response(
                    {"detail": "position not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity > position.quantity:
                return Response(
                    {"detail": "not enough quantity"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            realized_pnl = _quantize((price - position.avg_buy_price) * quantity)
            new_quantity = position.quantity - quantity
            if new_quantity == 0:
                # Fully closed positions are removed; the transaction keeps
                # the audit trail and the realised result.
                position.delete()
            else:
                position.quantity = new_quantity
                position.save(update_fields=["quantity", "updated_at"])

            trans = Transaction.objects.create(
                portfolio=portfolio,
                share=share,
                transaction_type=Transaction.SELL,
                quantity=quantity,
                price=price,
                total=_quantize(quantity * price),
                realized_pnl=realized_pnl,
            )

        return Response(
            {"status": "ok", "transaction_id": trans.id},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        portfolio = self.get_object()
        serializer = self.get_serializer(portfolio)
        data = serializer.data
        return Response(data)

    @action(detail=True, methods=["get"], url_path="positions")
    def positions(self, request, pk=None):
        portfolio = self.get_object()
        positions = portfolio.positions.all().select_related("share")
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="transactions")
    def transactions(self, request, pk=None):
        portfolio = self.get_object()
        transactions = portfolio.transactions.all().select_related("share")
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
