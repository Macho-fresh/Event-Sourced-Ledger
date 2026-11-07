from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

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
    EVENT_TYPES = [
        ("DEPOSIT", "Deposit"),
        ("TRANSFER_DEBIT", "Transfer Debit"),
        ("TRANSFER_CREDIT", "Transfer Credit"),
    ]

    event = models.CharField(choices=EVENT_TYPES, max_length=20)