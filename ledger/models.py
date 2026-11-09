from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.core.exceptions import ValidationError
from django.db.models import Q

class User(AbstractUser):
    email = models.EmailField()

class Account(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    currency = models.CharField(max_length=3, default='NGN')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.owner.username

class Transfer(models.Model):
    id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )

    idempotency_key = models.CharField(max_length=100, unique=True)
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='outgoing_transfers')
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='incoming_transfers')
    amount_kobo = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_account} -> {self.to_account}"

class LedgerEvents(models.Model):
    id = models.BigAutoField(primary_key=True)
    EVENT_TYPES = [
        ("DEPOSIT", "Deposit"),
        ("TRANSFER_DEBIT", "Transfer Debit"),
        ("TRANSFER_CREDIT", "Transfer Credit"),
    ]

    event_type = models.CharField(choices=EVENT_TYPES, max_length=20)
    event_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='events')
    amount_kobo = models.BigIntegerField()
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.PROTECT,
        related_name='events',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount_kobo = 0),
                name='event_amount_not_zero'
            )
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError("Ledger events cannot be deleted.")
    def save(self, *args, **kwargs):
        if self.pk is not None:
          raise ValidationError("Ledger events cannot be modified.")  
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_type}: {self.amount_kobo}"


class BalanceProjection(models.Model):

    account = models.OneToOneField(
        Account,
        on_delete=models.PROTECT,
        primary_key=True,
        related_name="balance_projection"
    )

    balance_kobo = models.BigIntegerField(default=0)

    last_processed_event = models.ForeignKey(
        LedgerEvents,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account.owner}: {self.balance_kobo}"
