from django.conf import settings
from django.db import models


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return self.ticker or self.name


class Portfolio(models.Model):
    """Виртуальный инвестиционный портфель"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    name = models.CharField(max_length=255, default="Main Portfolio")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"

    def __str__(self):
        return f"{self.name} ({self.user})"


class Position(models.Model):
    """Позиция в портфеле"""

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="positions"
    )
    share = models.ForeignKey(Share, on_delete=models.PROTECT, related_name="positions")
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    avg_buy_price = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Позиция"
        verbose_name_plural = "Позиции"
        unique_together = (("portfolio", "share"),)

    def __str__(self):
        return f"{self.portfolio} - {self.share.ticker}: {self.quantity}"


class Transaction(models.Model):
    """Транзакция по портфелю"""

    BUY = "BUY"
    SELL = "SELL"
    TRANSACTION_TYPES = (
        (BUY, "Buy"),
        (SELL, "Sell"),
    )

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="transactions"
    )
    share = models.ForeignKey(Share, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    total = models.DecimalField(max_digits=18, decimal_places=6)
    realized_pnl = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=0,
        verbose_name="Реализованный финансовый результат",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} {self.share.ticker} {self.quantity} @ {self.price}"

