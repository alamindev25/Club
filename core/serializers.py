from rest_framework import serializers
from .models import Member, Goal, Event, Transaction, Payment, PaymentAccount, BlogPost, Alumni


class MemberSerializer(serializers.ModelSerializer):
    display_photo = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id", "name", "category", "role", "phone", "email", "photo", "photo_url",
            "display_photo", "bio", "address", "sector", "order", "created_at"
        ]
        extra_kwargs = {
            "category": {"required": False, "allow_blank": True},
            "photo": {"required": False, "allow_null": True},
            "photo_url": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "bio": {"required": False, "allow_blank": True},
            "address": {"required": False, "allow_blank": True},
        }

    def get_display_photo(self, obj):
        request = self.context.get("request")
        if obj.photo:
            try:
                if request:
                    return request.build_absolute_uri(obj.photo.url)
                return obj.photo.url
            except Exception:
                pass
        return obj.photo_url or ""

    def to_representation(self, obj):
        return super().to_representation(obj)


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ["id", "title", "sector", "owner", "progress"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "organization", "date", "status"]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "kind", "donor_name", "profession", "phone", "method",
                  "amount", "paid_at", "note", "event"]


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "tran_id", "name", "profession", "phone", "method",
            "trx_id", "amount", "note", "status", "gateway_provider"
        ]
        read_only_fields = ["id", "tran_id", "status"]


class PaymentAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "tran_id", "name", "profession", "phone", "method", "trx_id",
            "amount", "note", "status", "gateway_provider", "bank_tran_id",
            "card_type", "created_at"
        ]


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAccount
        fields = [
            "bkash", "rocket", "nagad", "bank",
            "auto_gateway_enabled", "gateway_mode", "gateway_provider",
            "sslcz_store_id", "sslcz_store_passwd",
            "bkash_app_key", "bkash_app_secret", "bkash_username", "bkash_password"
        ]


class BlogPostSerializer(serializers.ModelSerializer):
    display_photo = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "category", "author", "content", "photo", "photo_url",
            "display_photo", "created_at"
        ]
        extra_kwargs = {
            "photo": {"required": False, "allow_null": True},
            "photo_url": {"required": False, "allow_blank": True},
            "category": {"required": False, "allow_blank": True},
            "author": {"required": False, "allow_blank": True},
        }

    def get_display_photo(self, obj):
        request = self.context.get("request")
        if obj.photo:
            try:
                if request:
                    return request.build_absolute_uri(obj.photo.url)
                return obj.photo.url
            except Exception:
                pass
        return obj.photo_url or ""


class AlumniSerializer(serializers.ModelSerializer):
    display_photo = serializers.SerializerMethodField()

    class Meta:
        model = Alumni
        fields = [
            "id", "name", "former_role", "job_title", "education", "phone", "email",
            "photo", "photo_url", "display_photo", "bio", "profile_link", "order", "created_at"
        ]
        extra_kwargs = {
            "photo": {"required": False, "allow_null": True},
            "photo_url": {"required": False, "allow_blank": True},
            "former_role": {"required": False, "allow_blank": True},
            "job_title": {"required": False, "allow_blank": True},
            "education": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "bio": {"required": False, "allow_blank": True},
            "profile_link": {"required": False, "allow_blank": True},
        }

    def get_display_photo(self, obj):
        request = self.context.get("request")
        if obj.photo:
            try:
                if request:
                    return request.build_absolute_uri(obj.photo.url)
                return obj.photo.url
            except Exception:
                pass
        return obj.photo_url or ""
