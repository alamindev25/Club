from django.contrib import admin
from .models import Member, Goal, Event, Transaction, Payment, PaymentAccount

admin.site.register([Goal, Event, PaymentAccount])


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "role", "sector", "phone", "email", "order")
    list_filter = ("category", "role", "sector")
    search_fields = ("name", "phone", "email", "bio", "address")
    list_editable = ("order",)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("kind", "donor_name", "amount", "method", "paid_at", "event")
    list_filter = ("kind", "method")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "method", "trx_id", "status", "created_at")
    list_filter = ("status", "method")
