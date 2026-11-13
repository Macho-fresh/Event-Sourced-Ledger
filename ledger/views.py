from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import *
from rest_framework.response import Response
from rest_framework import status
import uuid
from .serializer import EventSerializer


class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        User.objects.create(
            username = username,
            password = password,
            email = email
        )

        return Response({
            'message': 'User created successfully'
        }, status = status.HTTP_201_CREATED)

with transaction.atomic():
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


class DepositView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        event_type = request.data.get('event_type')
        amount = request.data.get('amount')
        account_id = request.data.get('account_id')

        idempotency_key = str(uuid.uuid4())

        account = Account.objects.get(id=account_id)

        if amount > 0:
            amount_kobo = amount * 100

        keys = Account.objects.all()
        for i in keys:
            if i.idempotency_key == idempotency_key:
                return Response({
                    'error': 'something went wrong, try again'
                }, status=status.HTTP_406_NOT_ACCEPTABLE)
            

        if event_type == 'deposit' and request.user == account.owner:

            LedgerEvents.objects.create(
                event_type = event_type,
                account = account,
                amount_kobo = amount_kobo,
            )

            BalanceProjection.objects.create(
                account = account,
                balance_kobo = amount_kobo
            )

            return Response({
                'message': 'Deposit Successfull'
            },status = status.HTTP_202_ACCEPTED)

with transaction.atomic():
    class TransferView(APIView):
        permission_classes = [IsAuthenticated]
        def post(self, request):
            event_type = request.data.get('event_type')
            amount = request.data.get('amount')
            from_account_id = request.data.get('from_account_id')
            to_account_id = request.data.get('to_account_id')

            idempotency_key = str(uuid.uuid4())

            from_account = Account.objects.get(id=from_account_id)
            to_account = Account.objects.get(id=to_account_id)


            if amount > 0:
                amount_kobo = amount * 100

            if from_account_id == to_account_id:
                return Response({
                    'error': 'cannot transfer to same account'
                },status=status.HTTP_401_UNAUTHORIZED)

            balance_from = BalanceProjection.objects.get(acccount=from_account)
            balance_to = BalanceProjection.objects.get(acount=to_account)
            if balance_from.balance_kobo >= amount_kobo:
                balance_from.balance_kobo -= amount_kobo
                balance_to.balance_kobo += amount_kobo

                transfer = Transfer.objects.create(
                    idempotency_key = idempotency_key,
                    from_account = from_account,
                    to_account = to_account,
                    amount = amount_kobo
                )

                LedgerEvents.objects.create(
                    event_type = 'Transfer Debit',
                    account = from_account,
                    amount_kobo = amount_kobo,
                    transfer = transfer,
                )

                LedgerEvents.objects.create(
                    event_type = 'Transfer Credit',
                    account = to_account,
                    amount_kobo = amount_kobo,
                    transfer = transfer,
                )

                return Response({
                    'message': 'Transfer Successfull'
                }, status=status.HTTP_202_ACCEPTED)

class GetBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
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
    def post(self, request):
        account_id = request.data.get('account_id')

        account = Account.objects.get(id=account_id)
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