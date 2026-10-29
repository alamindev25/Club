"""
Professional SSLCommerz Payment Gateway Integration for সমাজ কল্যাণ সংস্থা
Complies with SSLCommerz V4 API Documentation.
Handles Session Initialization, Validation Server API, and IPN.
"""
import json
import logging
import requests
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class SSLCommerzService:
    """
    Production-ready SSLCommerz Gateway Client.
    Supports both Sandbox (testing) and Live (production) modes.
    """
    SANDBOX_SESSION_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
    SANDBOX_VALIDATION_URL = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"

    LIVE_SESSION_URL = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
    LIVE_VALIDATION_URL = "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"

    def __init__(self, store_id=None, store_passwd=None, is_sandbox=None):
        from .models import PaymentAccount
        acc = PaymentAccount.load()

        # Prioritize explicit parameters -> DB settings -> settings.py
        self.store_id = (store_id or acc.sslcz_store_id or getattr(settings, "SSLCZ_STORE_ID", "")).strip()
        self.store_passwd = (store_passwd or acc.sslcz_store_passwd or getattr(settings, "SSLCZ_STORE_PASSWD", "")).strip()

        if is_sandbox is not None:
            self.is_sandbox = bool(is_sandbox)
        elif acc.sslcz_store_id:
            self.is_sandbox = (acc.gateway_mode != "live")
        else:
            self.is_sandbox = getattr(settings, "SSLCZ_IS_SANDBOX", True)

        self.session_url = self.SANDBOX_SESSION_URL if self.is_sandbox else self.LIVE_SESSION_URL
        self.validation_url = self.SANDBOX_VALIDATION_URL if self.is_sandbox else self.LIVE_VALIDATION_URL

    @property
    def is_configured(self):
        """Returns True if Store ID and Store Password are present."""
        return bool(self.store_id and self.store_passwd)

    def initiate_transaction(self, payment, request):
        """
        Creates a payment session with SSLCommerz.
        Returns:
            {"success": True, "gateway_url": str, "sessionkey": str} or
            {"success": False, "error": str}
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "SSLCommerz Store ID or Store Password is not configured."
            }

        base_url = request.build_absolute_uri("/").rstrip("/")
        success_url = f"{base_url}/api/payments/sslcommerz/success/"
        fail_url = f"{base_url}/api/payments/sslcommerz/fail/"
        cancel_url = f"{base_url}/api/payments/sslcommerz/cancel/"
        ipn_url = f"{base_url}/api/payments/sslcommerz/ipn/"

        # Ensure amount is formatted as 2 decimal places
        amount_str = f"{Decimal(str(payment.amount)):.2f}"

        # Standard SSLCommerz V4 Parameters
        post_data = {
            # Merchant Credentials
            "store_id": self.store_id,
            "store_passwd": self.store_passwd,

            # Order / Transaction Information
            "total_amount": amount_str,
            "currency": "BDT",
            "tran_id": payment.tran_id,

            # Redirection & Webhook URLs
            "success_url": success_url,
            "fail_url": fail_url,
            "cancel_url": cancel_url,
            "ipn_url": ipn_url,

            # Customer Information
            "cus_name": payment.name or "Well-wisher",
            "cus_email": "donor@samaj.org",
            "cus_add1": "Dhaka, Bangladesh",
            "cus_city": "Dhaka",
            "cus_state": "Dhaka",
            "cus_postcode": "1000",
            "cus_country": "Bangladesh",
            "cus_phone": payment.phone or "01700000000",

            # Shipment Information
            "shipping_method": "NO",
            "num_of_item": "1",

            # Product Information
            "product_name": "Charity Donation",
            "product_category": "Donation",
            "product_profile": "non-physical-goods",

            # Custom Tracking Parameters
            "value_a": str(payment.id),
            "value_b": payment.method or "online",
            "value_c": "samaj_welfare"
        }

        try:
            logger.info("Connecting to SSLCommerz API: %s for tran_id: %s, amount: %s", self.session_url, payment.tran_id, amount_str)
            response = requests.post(self.session_url, data=post_data, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "SUCCESS" and data.get("GatewayPageURL"):
                return {
                    "success": True,
                    "gateway_url": data["GatewayPageURL"],
                    "sessionkey": data.get("sessionkey", "")
                }
            else:
                error_msg = data.get("failedreason") or data.get("message") or "Gateway rejected payment session initiation"
                logger.error("SSLCommerz initialization failed: %s", error_msg)
                return {"success": False, "error": error_msg}

        except requests.exceptions.RequestException as e:
            logger.exception("SSLCommerz HTTP error")
            return {"success": False, "error": f"পেমেন্ট গেটওয়ে সার্ভারে সংযোগ করা যায়নি: {str(e)}"}
        except Exception as e:
            logger.exception("SSLCommerz general error")
            return {"success": False, "error": str(e)}

    def validate_transaction(self, val_id):
        """
        Validates transaction authenticity directly with SSLCommerz Validation Server.
        """
        if not self.is_configured:
            return {"is_valid": False, "error": "SSLCommerz credentials missing"}

        params = {
            "val_id": val_id,
            "store_id": self.store_id,
            "store_passwd": self.store_passwd,
            "format": "json"
        }

        try:
            logger.info("Validating SSLCommerz transaction val_id: %s on %s", val_id, self.validation_url)
            response = requests.get(self.validation_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            status = str(data.get("status", "")).upper()
            if status in ["VALID", "VALIDATED"]:
                return {
                    "is_valid": True,
                    "data": data,
                    "tran_id": data.get("tran_id"),
                    "amount": data.get("amount"),
                    "currency": data.get("currency"),
                    "bank_tran_id": data.get("bank_tran_id"),
                    "card_type": data.get("card_type"),
                    "card_brand": data.get("card_brand"),
                    "card_issuer": data.get("card_issuer")
                }
            else:
                error_msg = data.get("error") or f"Invalid response status: {status}"
                logger.warning("SSLCommerz validation rejected: %s", error_msg)
                return {
                    "is_valid": False,
                    "error": error_msg,
                    "data": data
                }

        except Exception as e:
            logger.exception("SSLCommerz validation server error")
            return {"is_valid": False, "error": str(e)}

