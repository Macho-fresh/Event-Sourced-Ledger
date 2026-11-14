from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import *
from rest_framework.response import Response
from rest_framework import status
import uuid
from .serializer import EventSerializer
from decimal import Decimal


class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        User.objects.create_user(
            username = username,
            password = password,
            email = email
        )

        return Response({
            'message': 'User created successfully'
        }, status = status.HTTP_201_CREATED)

@transaction.atomic
class CreatAccountView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        currency = request.data.get('currency')
        
        account = Account.objects.create(
            owner = user,
            currency = currency
        )

        BalanceProjection.objects.create(
            account = account,
            balance_kobo = 0
        )

        return Response({
            'message': 'Account created successfully'
        }, status = status.HTTP_201_CREATED)

@transaction.atomic
class DepositView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        amount = Decimal(str(request.data.get('amount')))
        account_id = request.data.get('account_id')
        idempotency_key = request.data.get('key')

        # idempotency_key = str(uuid.uuid4())

        account = Account.objects.get(id=account_id)

        if amount > 0:
            amount_kobo = int(amount * 100)
        else:
            return Response({
                'error': 'Amount must be greater than 0'
            }, status=status.HTTP_403_FORBIDDEN)
        keys = Transfer.objects.all()
        for i in keys:
            if i.idempotency_key == idempotency_key:
                return Response({
                    'error': 'something went wrong, try again'
                }, status=status.HTTP_406_NOT_ACCEPTABLE)
            

        if request.user == account.owner:

            LedgerEvents.objects.create(
                event_type = 'DEPOSIT',
                account = account,
                amount_kobo = amount_kobo,
            )

            projection = BalanceProjection.objects.get(
                account=account
            )

            projection.balance_kobo += amount_kobo
            projection.save()

            return Response({
                'message': 'Deposit Successfull'
            },status = status.HTTP_202_ACCEPTED)

@transaction.atomic
class TransferView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        amount = request.data.get('amount')
        from_account_id = request.data.get('from_account_id')
        to_account_id = request.data.get('to_account_id')
        idempotency_key = request.data.get('key')

        from_account = Account.objects.get(id=from_account_id)
        to_account = Account.objects.get(id=to_account_id)

        if amount > 0:
            amount_kobo = amount * 100

        if from_account_id == to_account_id:
            return Response({
                'error': 'cannot transfer to same account'
            },status=status.HTTP_401_UNAUTHORIZED)

        if from_account != request.user:
            return Response({
                'error': 'you do not own this account'
            },status=status.HTTP_401_UNAUTHORIZED)

        keys = Transfer.objects.all()
        for i in keys:
            if i.idempotency_key == idempotency_key:
                return Response({
                    'error': 'something went wrong, try again'
                }, status=status.HTTP_406_NOT_ACCEPTABLE)

        balance_from = BalanceProjection.objects.get(account=from_account)
        balance_to = BalanceProjection.objects.get(account=to_account)
        if balance_from.balance_kobo >= amount_kobo:
            balance_from.balance_kobo -= amount_kobo
            balance_to.balance_kobo += amount_kobo
            balance_from.save()
            balance_to.save()

            transfer = Transfer.objects.create(
                idempotency_key = idempotency_key,
                from_account = from_account,
                to_account = to_account,
                amount = amount_kobo
            )

            LedgerEvents.objects.create(
                event_type = 'TRANSFER_DEBIT',
                account = from_account,
                amount_kobo = -amount_kobo,
                transfer = transfer,
            )

            LedgerEvents.objects.create(
                event_type = 'TRANSFER_CREDIT',
                account = to_account,
                amount_kobo = amount_kobo,
                transfer = transfer,
            )

            return Response({
                'message': 'Transfer Successfull'
            }, status=status.HTTP_202_ACCEPTED)

@transaction.atomic
class GetBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        account_id = request.data.get('account_id')
        account = Account.objects.get(id=account_id)
        if request.user == account.owner:
            projection = account.balance_projection
            balance = projection.balance_kobo

            return Response({
                'balance': f'{balance}'
            },status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'You are not the owner of this account'
            },status=status.HTTP_401_UNAUTHORIZED)

#  create serializer for the event_history endpoint

class EventHistory(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        account_id = request.data.get('account_id')

        account = Account.objects.get(id=account_id)
        if account.owner != request.user:
            return Response({
                'error': 'you do not own this account'
            },status=status.HTTP_401_UNAUTHORIZED)
        if LedgerEvents.objects.filter(account = account):
            events = LedgerEvents.objects.filter(account = account)
            serializer = EventSerializer(events, many=True)
            return Response({
                'message': 'Events retrieved successfully',
                'data': serializer.data
            },status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'This account doesnt have any events yet..'
            },status=status.HTTP_404_NOT_FOUND)

        # implement reconcilation and implement rebuild projections

class ReconcilationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        account_id = request.data.get('account_id')
        account = Account.objects.get(id=account_id)
        balance = BalanceProjection.objects.get(account=account).balance_kobo
        to_check = 0
        events = LedgerEvents.objects.filter(account=account).order_by('id')
        for i in events:
            to_check+=i.amount_kobo
        if request.user == account.owner:
            return Response({
                'error': 'You are not the owner of this account'
            })
        if to_check != balance:
            return Response({
                'error': 'Balance mismatch detected'
            },status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': 'Balances match'
        },status=status.HTTP_200_OK)

class RebuildProjection(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        account_id = request.data.get('account_id')
        account = Account.objects.get(id=account_id)
        balance = BalanceProjection.objects.get(account=account).balance_kobo
        balance = 0
        events = LedgerEvents.objects.filter(account=account).order_by('id')
        for i in events:
            balance+=i.amount_kobo
        balance.save()