from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views as v

r = DefaultRouter()
r.register("members", v.MemberViewSet)
r.register("alumni", v.AlumniViewSet)
r.register("posts", v.BlogPostViewSet)
r.register("goals", v.GoalViewSet)
r.register("events", v.EventViewSet)
r.register("admin/transactions", v.TransactionViewSet)
r.register("admin/payments", v.PaymentAdminViewSet)

urlpatterns = [
    path("login/", v.LoginView.as_view()),
    path("summary/", v.SummaryView.as_view()),
    path("settings/", v.SettingsView.as_view()),
    # Automated Payment Endpoints
    path("payments/initiate/", v.PaymentInitiateView.as_view(), name="payment-initiate"),
    path("payments/verify/", v.PaymentVerifyView.as_view(), name="payment-verify"),
    # Official SSLCommerz Callback Endpoints
    path("payments/sslcommerz/success/", v.SSLCommerzSuccessView.as_view(), name="sslcz-success"),
    path("payments/sslcommerz/fail/", v.SSLCommerzFailView.as_view(), name="sslcz-fail"),
    path("payments/sslcommerz/cancel/", v.SSLCommerzCancelView.as_view(), name="sslcz-cancel"),
    path("payments/sslcommerz/ipn/", v.SSLCommerzIPNView.as_view(), name="sslcz-ipn"),
    # Legacy Gateway Return Fallbacks
    path("payments/gateway-return/", v.GatewayReturnView.as_view()),
    path("payments/ipn/", v.PaymentIPNView.as_view()),
    path("payments/", v.PaymentCreate.as_view()),
    path("", include(r.urls)),
]
