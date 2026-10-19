from decimal import Decimal
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def ch(*v):
    return [(x, x) for x in v]

ROLES = ch(
    "প্রধান উপদেষ্টা", "উপদেষ্টা", "সভাপতি", "সহ-সভাপতি", 
    "সাধারণ সম্পাদক", "সহ-সাধারণ সম্পাদক", "সাংগঠনিক সম্পাদক", 
    "অর্থ সম্পাদক / কোষাধ্যক্ষ", "দপ্তর সম্পাদক", "প্রচার ও প্রকাশনা সম্পাদক", 
    "সমাজকল্যাণ সম্পাদক", "সচিবালয় সদস্য", "কার্যনির্বাহী সদস্য", 
    "সাধারণ সদস্য", "আজীবন সদস্য"
)
CATEGORIES = ch(
    "উপদেষ্টা ও সভাপতি",
    "সাধারণ সম্পাদক ও সম্পাদকীয়",
    "কার্যনির্বাহী সদস্য",
    "সাধারণ সদস্য"
)
SECTORS = ch("শিক্ষা", "স্বাস্থ্য", "ক্রীড়া", "পরিবেশ", "সমাজসেবা", "ত্রাণ ও দুর্যোগ")
METHODS = ch("বিকাশ", "রকেট", "নগদ (Nagad)", "ব্যাংক ট্রান্সফার", "হাতে নগদ", "অন্যান্য")
EVENT_STATUS = ch("আসন্ন", "চলমান", "সম্পন্ন")


def money():
    return models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])


class Member(models.Model):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=120, default="কার্যনির্বাহী সদস্য", blank=True)
    role = models.CharField(max_length=120, default="সাধারণ সদস্য")
    phone = models.CharField(max_length=30, blank=True)
    email = models.CharField(max_length=120, blank=True)
    photo = models.ImageField(upload_to="members/", blank=True, null=True)
    photo_url = models.TextField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    address = models.CharField(max_length=200, blank=True)
    sector = models.CharField(max_length=120, default="সমাজসেবা")
    order = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} ({self.role})"

    @property
    def display_photo(self):
        if self.photo:
            try:
                return self.photo.url
            except Exception:
                pass
        return self.photo_url or ""


class Goal(models.Model):
    title = models.CharField(max_length=200)
    sector = models.CharField(max_length=30, choices=SECTORS)
    owner = models.CharField(max_length=120, blank=True)
    progress = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])

    def __str__(self):
        return self.title


class Event(models.Model):
    title = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True)
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default="আসন্ন")

    def __str__(self):
        return self.title


class Transaction(models.Model):
    """আয় বা ব্যয়ের চূড়ান্ত হিসাব। দাতার তথ্য শুধু অ্যাডমিন API-তে যায়।"""
    kind = models.CharField(max_length=3, choices=[("in", "আয়"), ("out", "ব্যয়")])
    donor_name = models.CharField(max_length=120, blank=True)
    profession = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    method = models.CharField(max_length=30, blank=True)
    amount = money()
    paid_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=300, blank=True)
    event = models.CharField(max_length=200, blank=True)  # ব্যয়ের কর্মসূচি

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.kind} {self.amount}"


class Payment(models.Model):
    """দাতার জমা দেওয়া অনুদান, অ্যাডমিন যাচাইয়ের আগ পর্যন্ত pending।"""
    name = models.CharField(max_length=120)
    profession = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    method = models.CharField(max_length=30, choices=METHODS)
    trx_id = models.CharField(max_length=80, blank=True)
    amount = money()
    note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=ch("pending", "approved", "rejected"), default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PaymentAccount(models.Model):
    bkash = models.CharField(max_length=60, blank=True)
    rocket = models.CharField(max_length=60, blank=True)
    nagad = models.CharField(max_length=60, blank=True)
    bank = models.CharField(max_length=300, blank=True)

    @classmethod
    def load(cls):
        return cls.objects.first() or cls.objects.create()
