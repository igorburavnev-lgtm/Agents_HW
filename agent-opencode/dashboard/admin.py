from django.contrib import admin

from dashboard.models import Portfolio, Position, Share, Transaction


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "currency")
    search_fields = ("figi", "isin", "name", "ticker")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
    )


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "created_at")
    search_fields = ("name", "user__username")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("id", "portfolio", "share", "quantity", "avg_buy_price", "updated_at")
    search_fields = ("portfolio__name", "share__ticker")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "portfolio", "share", "transaction_type", "quantity", "price", "total", "created_at")
    search_fields = ("portfolio__name", "share__ticker")
    list_filter = ("transaction_type",)

