import json
import uuid
from decimal import Decimal
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, parsers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import serializers as S
from .models import Event, Goal, Member, Payment, PaymentAccount, Transaction, BlogPost, Alumni


def generate_tran_id():
    now_str = timezone.now().strftime("%Y%m%d%H%M%S")
    rand_str = uuid.uuid4().hex[:6].upper()
    return f"SAM_{now_str}_{rand_str}"


def complete_payment_auto(tran_id, trx_id=None, bank_tran_id=None, card_type=None, raw_data=None):
    """লেনদেন স্বয়ংক্রিয়ভাবে সম্পন্ন করা এবং সরাসরি অফিসিয়াল আয় হিসেবে যুক্ত করা।"""
    with transaction.atomic():
        p = Payment.objects.select_for_update().filter(tran_id=tran_id).first()
        if not p:
            return None, "পেমেন্ট পাওয়া যায়নি।"
        if p.status in ["approved", "completed"]:
            return p, "Already completed"

        final_trx = trx_id or bank_tran_id or f"TXN_{uuid.uuid4().hex[:10].upper()}"
        p.status = "completed"
        p.trx_id = final_trx
        p.bank_tran_id = bank_tran_id or final_trx
        if card_type:
            p.card_type = card_type
        if raw_data:
            p.ipn_data = json.dumps(raw_data) if isinstance(raw_data, dict) else str(raw_data)
        p.save()

        note_parts = [f"অনলাইন অটো পেমেন্ট ({p.method})", f"TrxID: {p.trx_id}"]
        if p.note:
            note_parts.append(p.note)
        note = " · ".join(note_parts)

        Transaction.objects.create(
            kind="in",
            donor_name=p.name or "শুভাকাঙ্ক্ষী",
            profession=p.profession,
            phone=p.phone,
            method=p.method,
            amount=p.amount,
            paid_at=timezone.now(),
            note=note
        )
        return p, "Success"


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


class PaymentInitiateView(APIView):
    """অনলাইন স্বয়ংক্রিয় পেমেন্ট সেশন শুরু করার ভিউ (SSLCommerz বা অটো স্মার্ট গেটওয়ে)।"""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        amount_raw = request.data.get("amount")
        method = request.data.get("method") or "বিকাশ"
        phone = request.data.get("phone") or ""
        profession = request.data.get("profession") or ""
        note = request.data.get("note") or ""

        if not name:
            return Response({"detail": "আপনার নাম আবশ্যক।"}, status=400)
        try:
            amount = Decimal(str(amount_raw))
            if amount <= 0:
                raise ValueError()
        except Exception:
            return Response({"detail": "সঠিক অনুদানের পরিমাণ লিখুন।"}, status=400)

        tran_id = generate_tran_id()
        acc = PaymentAccount.load()

        p = Payment.objects.create(
            tran_id=tran_id,
            name=name,
            profession=profession,
            phone=phone,
            method=method,
            amount=amount,
            note=note,
            status="initiated",
            gateway_provider=acc.gateway_provider or "auto"
        )

        # SSLCommerz ক্রেডেনশিয়াল (settings.py অথবা ডাটাবেস থেকে)
        store_id = acc.sslcz_store_id or getattr(settings, "SSLCZ_STORE_ID", "")
        store_passwd = acc.sslcz_store_passwd or getattr(settings, "SSLCZ_STORE_PASSWD", "")
        is_live = (acc.gateway_mode == "live") if acc.sslcz_store_id else not getattr(settings, "SSLCZ_IS_SANDBOX", True)

        if acc.auto_gateway_enabled and store_id and store_passwd:
            gw_url = "https://securepay.sslcommerz.com/gwprocess/v4/api.php" if is_live else "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            base_url = request.build_absolute_uri("/").rstrip("/")
            post_data = {
                "store_id": store_id,
                "store_passwd": store_passwd,
                "total_amount": str(p.amount),
                "currency": "BDT",
                "tran_id": p.tran_id,
                "success_url": f"{base_url}/api/payments/gateway-return/?status=success",
                "fail_url": f"{base_url}/api/payments/gateway-return/?status=fail",
                "cancel_url": f"{base_url}/api/payments/gateway-return/?status=cancel",
                "ipn_url": f"{base_url}/api/payments/ipn/",
                "cus_name": p.name,
                "cus_email": "donor@samaj.org",
                "cus_phone": p.phone or "01700000000",
                "cus_add1": "Dhaka",
                "cus_city": "Dhaka",
                "cus_country": "Bangladesh",
                "shipping_method": "NO",
                "product_name": "Online Donation",
                "product_category": "Donation",
                "product_profile": "general"
            }
            try:
                r = requests.post(gw_url, data=post_data, timeout=12)
                data = r.json()
                if data.get("status") == "SUCCESS" and data.get("GatewayPageURL"):
                    return Response({
                        "mode": "live_gateway",
                        "tran_id": p.tran_id,
                        "gateway_url": data["GatewayPageURL"]
                    })
            except Exception:
                pass

        # অটোমেটিক ইন্টারেক্টিভ সিমুলেটর / স্মার্ট চেকআউট
        return Response({
            "mode": "simulator",
            "tran_id": p.tran_id,
            "name": p.name,
            "amount": float(p.amount),
            "method": p.method,
            "phone": p.phone
        })


class PaymentVerifyView(APIView):
    """পেমেন্ট শেষ হওয়া মাত্রই সরাসরি অনুদান অনুমোদন ও ফান্ডে ক্রেডিট করার ভিউ (নো ম্যানুয়াল অনুমোদন)।"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        tran_id = request.data.get("tran_id")
        trx_id = request.data.get("trx_id")
        bank_tran_id = request.data.get("bank_tran_id")
        card_type = request.data.get("card_type")

        if not tran_id:
            return Response({"detail": "ট্রানজেকশন আইডি পাওয়া যায়নি।"}, status=400)

        p, msg = complete_payment_auto(
            tran_id=tran_id,
            trx_id=trx_id,
            bank_tran_id=bank_tran_id,
            card_type=card_type,
            raw_data=request.data
        )
        if not p:
            return Response({"detail": msg}, status=404)

        return Response({
            "status": "completed",
            "tran_id": p.tran_id,
            "trx_id": p.trx_id,
            "amount": float(p.amount),
            "name": p.name,
            "method": p.method,
            "paid_at": p.created_at.strftime("%Y-%m-%d %I:%M %p")
        })


@method_decorator(csrf_exempt, name="dispatch")
class GatewayReturnView(APIView):
    """বহিরাগত গেটওয়ে (SSLCommerz) থেকে রিডাইরেক্ট হয়ে ফিরে আসার হ্যান্ডলার।"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        return self.handle_return(request)

    def get(self, request):
        return self.handle_return(request)

    def handle_return(self, request):
        data = request.data if request.method == "POST" else request.GET
        status_param = (request.GET.get("status") or data.get("status", "")).lower()
        tran_id = data.get("tran_id") or request.GET.get("tran_id")
        val_id = data.get("val_id")
        bank_tran_id = data.get("bank_tran_id")
        card_type = data.get("card_type")

        if not tran_id:
            return HttpResponseRedirect("/#pay?status=fail")

        if status_param == "success":
            p, msg = complete_payment_auto(
                tran_id=tran_id,
                trx_id=val_id or bank_tran_id,
                bank_tran_id=bank_tran_id,
                card_type=card_type,
                raw_data=dict(data)
            )
            if p:
                return HttpResponseRedirect(f"/#pay?status=success&tran_id={p.tran_id}&trx_id={p.trx_id}&amount={p.amount}")
            return HttpResponseRedirect("/#pay?status=fail")
        else:
            Payment.objects.filter(tran_id=tran_id).update(status="failed" if status_param == "fail" else "cancelled")
            return HttpResponseRedirect(f"/#pay?status={status_param}")


@method_decorator(csrf_exempt, name="dispatch")
class PaymentIPNView(APIView):
    """গেটওয়ে সার্ভার-টু-সার্ভার আইপিএন (Instant Payment Notification) নোটিফিকেশন।"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        tran_id = request.data.get("tran_id")
        val_id = request.data.get("val_id")
        status_val = str(request.data.get("status", "")).upper()
        if tran_id and status_val == "VALID":
            complete_payment_auto(tran_id, trx_id=val_id, raw_data=dict(request.data))
            return Response({"status": "IPN Handled"})
        return Response({"status": "ignored"})


class PaymentCreate(CreateAPIView):
    """ব্যাকওয়ার্ড কম্প্যাটিবিলিটির জন্য সাধারণ পেমেন্ট সাবমিশন।"""
    serializer_class = S.PaymentCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"


class PaymentAdminViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Payment.objects.all().order_by("-created_at")
    serializer_class = S.PaymentAdminSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        with transaction.atomic():
            p = Payment.objects.select_for_update().filter(pk=pk).first()
            if not p:
                return Response({"detail": "পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)
            if p.status in ["approved", "completed"]:
                return Response({"status": "already_approved"})
            note = " · ".join(x for x in [p.note, f"TrxID: {p.trx_id}" if p.trx_id else ""] if x)
            Transaction.objects.create(
                kind="in", donor_name=p.name, profession=p.profession, phone=p.phone,
                method=p.method, amount=p.amount, paid_at=p.created_at, note=note)
            p.status = "approved"
            p.save(update_fields=["status"])
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        n = Payment.objects.filter(pk=pk).update(status="rejected")
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
        acc = PaymentAccount.load()
        data = S.AccountSerializer(acc).data
        if not data.get("sslcz_store_id") and getattr(settings, "SSLCZ_STORE_ID", ""):
            data["sslcz_store_id"] = getattr(settings, "SSLCZ_STORE_ID", "")
        if not data.get("sslcz_store_passwd") and getattr(settings, "SSLCZ_STORE_PASSWD", ""):
            data["sslcz_store_passwd"] = getattr(settings, "SSLCZ_STORE_PASSWD", "")
        if not acc.sslcz_store_id and hasattr(settings, "SSLCZ_IS_SANDBOX"):
            data["gateway_mode"] = "sandbox" if getattr(settings, "SSLCZ_IS_SANDBOX", True) else "live"
        return Response(data)

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


class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = S.BlogPostSerializer
    permission_classes = [StaffOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]


class AlumniViewSet(viewsets.ModelViewSet):
    queryset = Alumni.objects.all()
    serializer_class = S.AlumniSerializer
    permission_classes = [StaffOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
