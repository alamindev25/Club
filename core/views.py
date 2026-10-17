from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse
from rest_framework import mixins, parsers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import serializers as S
from .models import Event, Goal, Member, Payment, PaymentAccount, Transaction


class StaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_staff)


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = S.MemberSerializer
    permission_classes = [StaffOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]


class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = S.GoalSerializer
    permission_classes = [StaffOrReadOnly]


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = S.EventSerializer
    permission_classes = [StaffOrReadOnly]


class TransactionViewSet(viewsets.ModelViewSet):
    """শুধু অ্যাডমিন: দাতার নাম, পেশা, ফোন, মাধ্যম সহ পুরো হিসাব।"""
    queryset = Transaction.objects.all()
    serializer_class = S.TransactionSerializer
    permission_classes = [IsAdminUser]


class PaymentCreate(CreateAPIView):
    """যে কেউ অনুদানের তথ্য জমা দিতে পারে (pending হিসেবে)।"""
    serializer_class = S.PaymentCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"


class PaymentAdminViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Payment.objects.filter(status="pending")
    serializer_class = S.PaymentAdminSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        with transaction.atomic():
            p = Payment.objects.select_for_update().filter(pk=pk, status="pending").first()
            if not p:
                return Response({"detail": "পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)
            note = " · ".join(x for x in [p.note, f"TrxID: {p.trx_id}" if p.trx_id else ""] if x)
            Transaction.objects.create(
                kind="in", donor_name=p.name, profession=p.profession, phone=p.phone,
                method=p.method, amount=p.amount, paid_at=p.created_at, note=note)
            p.status = "approved"
            p.save(update_fields=["status"])
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        n = Payment.objects.filter(pk=pk, status="pending").update(status="rejected")
        if not n:
            return Response({"detail": "পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "rejected"})


class SummaryView(APIView):
    """সবার জন্য: শুধু মোট আয়, মোট ব্যয় ও কর্মসূচিভিত্তিক খরচ। কোনো দাতার তথ্য নেই।"""
    permission_classes = [AllowAny]

    def get(self, request):
        total = lambda k: Transaction.objects.filter(kind=k).aggregate(s=Sum("amount"))["s"] or 0
        by = {}
        for r in Transaction.objects.filter(kind="out").values("event").annotate(s=Sum("amount")):
            k = r["event"] or "সাধারণ খরচ"
            by[k] = by.get(k, 0) + float(r["s"])
        return Response({"income": float(total("in")), "expense": float(total("out")), "by_event": by})


class SettingsView(APIView):
    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAdminUser()]

    def get(self, request):
        return Response(S.AccountSerializer(PaymentAccount.load()).data)

    def put(self, request):
        s = S.AccountSerializer(PaymentAccount.load(), data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        u = authenticate(username=request.data.get("username"), password=request.data.get("password"))
        if not u or not u.is_staff:
            return Response({"detail": "ইউজারনেম বা পাসওয়ার্ড ভুল।"}, status=400)
        token, _ = Token.objects.get_or_create(user=u)
        return Response({"token": token.key})


def index(request):
    return FileResponse(open(settings.BASE_DIR / "frontend" / "index.html", "rb"),
                        content_type="text/html; charset=utf-8")
