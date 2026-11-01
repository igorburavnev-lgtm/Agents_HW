from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from dashboard.models import Portfolio, Position, Share, Transaction


class ShareSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Share
        fields = ("id", "ticker", "name", "last_price", "currency")


class TransactionSerializer(serializers.ModelSerializer):
    share = ShareSimpleSerializer(read_only=True)
    share_id = serializers.PrimaryKeyRelatedField(
        queryset=Share.objects.all(), source="share", write_only=True
    )

    class Meta:
        model = Transaction
        fields = (
            "id",
            "portfolio",
            "share",
            "share_id",
            "transaction_type",
            "quantity",
            "price",
            "total",
            "realized_pnl",
            "created_at",
        )
        read_only_fields = (
            "id",
            "total",
            "realized_pnl",
            "created_at",
            "portfolio",
        )
        extra_kwargs = {
            # Optional on input: the view falls back to Share.last_price.
            "price": {"required": False, "allow_null": True},
            "quantity": {"min_value": Decimal("0.000001")},
        }


class PositionSerializer(serializers.ModelSerializer):
    share = ShareSimpleSerializer(read_only=True)
    current_price = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    cost_basis = serializers.SerializerMethodField()
    unrealized_pl = serializers.SerializerMethodField()
    unrealized_pl_pct = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = (
            "id",
            "portfolio",
            "share",
            "quantity",
            "avg_buy_price",
            "current_price",
            "current_value",
            "cost_basis",
            "unrealized_pl",
            "unrealized_pl_pct",
            "updated_at",
        )

    def get_current_price(self, obj):
        if obj.share.last_price is None:
            return None
        return Decimal(str(obj.share.last_price))

    def get_current_value(self, obj):
        price = self.get_current_price(obj)
        if price is None:
            return None
        return obj.quantity * price

    def get_cost_basis(self, obj):
        return obj.quantity * obj.avg_buy_price

    def get_unrealized_pl(self, obj):
        current = self.get_current_value(obj)
        if current is None:
            return None
        return current - self.get_cost_basis(obj)

    def get_unrealized_pl_pct(self, obj):
        cost = self.get_cost_basis(obj)
        if not cost or cost == 0:
            return None
        pl = self.get_unrealized_pl(obj)
        if pl is None:
            return None
        return (pl / cost) * Decimal(100)


class PortfolioSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    total_cost_basis = serializers.SerializerMethodField()
    total_current_value = serializers.SerializerMethodField()
    total_unrealized_pl = serializers.SerializerMethodField()
    total_unrealized_pl_pct = serializers.SerializerMethodField()
    total_realized_pl = serializers.SerializerMethodField()
    total_pl = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = (
            "id",
            "name",
            "user",
            "created_at",
            "updated_at",
            "positions",
            "total_cost_basis",
            "total_current_value",
            "total_unrealized_pl",
            "total_unrealized_pl_pct",
            "total_realized_pl",
            "total_pl",
        )
        read_only_fields = ("user",)

    def get_total_cost_basis(self, obj):
        total = Decimal(0)
        for pos in obj.positions.all():
            total += pos.quantity * pos.avg_buy_price
        return total

    def get_total_current_value(self, obj):
        total = Decimal(0)
        for pos in obj.positions.all():
            if pos.share.last_price is None:
                continue
            total += pos.quantity * Decimal(str(pos.share.last_price))
        return total

    def get_total_unrealized_pl(self, obj):
        return self.get_total_current_value(obj) - self.get_total_cost_basis(obj)

    def get_total_unrealized_pl_pct(self, obj):
        cost = self.get_total_cost_basis(obj)
        if not cost or cost == 0:
            return None
        pl = self.get_total_unrealized_pl(obj)
        return (pl / cost) * Decimal(100)

    def get_total_realized_pl(self, obj):
        total = obj.transactions.filter(
            transaction_type=Transaction.SELL
        ).aggregate(total=Sum("realized_pnl"))["total"]
        return total or Decimal(0)

    def get_total_pl(self, obj):
        return self.get_total_unrealized_pl(obj) + self.get_total_realized_pl(obj)
