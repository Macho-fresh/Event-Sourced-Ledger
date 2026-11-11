from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import *
from rest_framework.response import Response
from rest_framework import status
import uuid


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

class TransferView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        event_type = request.data.get('event_type')
        amount = request.data.get('amount')
        from_account_id = request.data.get('from_account_id')
        to_account_id = request.data.get('to_account_id')
