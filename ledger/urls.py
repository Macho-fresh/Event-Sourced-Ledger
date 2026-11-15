from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView


urlpatterns=[
    path('register/', RegisterView.as_view()),
    path('login/', TokenObtainPairView.as_view()),
    path('create-account/', CreateAccountView.as_view()),
    path('deposit/', DepositView.as_view()),
    path('transfer/', TransferView.as_view()),
    path('balance/', GetBalanceView.as_view()),
    path('history/', EventHistory.as_view()),
    path('reconcile/', ReconcilationView.as_view()),
    path('rebuild/', RebuildProjection.as_view())
]