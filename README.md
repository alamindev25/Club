# সমাজ কল্যাণ সংস্থা — Django + DRF ব্যাকএন্ড

## চালানোর নিয়ম
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser      # এটাই অ্যাডমিন লগইন
    python manage.py runserver            # http://127.0.0.1:8000

- সাইট: `/`   ·   Django admin: `/admin/`   ·   API: `/api/`
- অ্যাডমিন হিসেবে সাইটে ঢুকে "অ্যাডমিন ড্যাশবোর্ড" থেকে পেমেন্ট নম্বর (বিকাশ/রকেট/নগদ/ব্যাংক) বসান।

## API
| পথ | কে পারবে |
|---|---|
| GET `/api/summary/` | সবাই: মোট আয়, ব্যয়, কর্মসূচিভিত্তিক খরচ (দাতার তথ্য নেই) |
| GET `/api/members/ goals/ events/ settings/` | সবাই (সদস্যের ফোন শুধু অ্যাডমিনকে) |
| POST `/api/payments/` | সবাই: অনুদানের তথ্য জমা (pending), রেট লিমিট ২০/ঘণ্টা |
| POST `/api/login/` | অ্যাডমিন (staff) টোকেন পায় |
| `/api/members/ goals/ events/` লেখা, PUT `/api/settings/` | শুধু অ্যাডমিন |
| `/api/admin/transactions/` | শুধু অ্যাডমিন: দাতার নাম, পেশা, ফোন, মাধ্যম, সময় |
| GET `/api/admin/payments/`, POST `.../{id}/approve/` `.../{id}/reject/` | শুধু অ্যাডমিন |

## প্রোডাকশনে
    export DEBUG=0 SECRET_KEY='লম্বা-গোপন-কী' ALLOWED_HOSTS=yourdomain.com CSRF_TRUSTED_ORIGINS=https://yourdomain.com
    python manage.py collectstatic --noinput
    gunicorn samaj.wsgi
ডাটাবেস এখন SQLite; বড় হলে `settings.py`-তে PostgreSQL দিন। নিয়মিত `db.sqlite3` ব্যাকআপ রাখুন।
