from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views as v

r = DefaultRouter()
r.register("members", v.MemberViewSet)
r.register("goals", v.GoalViewSet)
r.register("events", v.EventViewSet)
r.register("admin/transactions", v.TransactionViewSet)
r.register("admin/payments", v.PaymentAdminViewSet)

urlpatterns = [
    path("login/", v.LoginView.as_view()),
    path("summary/", v.SummaryView.as_view()),
    path("settings/", v.SettingsView.as_view()),
    path("payments/", v.PaymentCreate.as_view()),
    path("", include(r.urls)),
]
