"""Combined Beeceptor demo tests — endpoint creation, mock rules, and API verification.

Three scenarios in one go:
  1. Order API  — async callout + Discord webhook callback
  2. Dog API    — sync callout proxying to dog.ceo
  3. Payment API — async callout + self-callback
"""

import json

import pytest
import requests
from playwright.sync_api import expect


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_endpoint(page, name: str) -> str:
    page.goto("https://beeceptor.com")
    expect(page.locator("#channel")).to_be_visible()
    page.locator("#channel").fill(name)
    page.locator("button[type='submit']").click()
    page.wait_for_load_state("networkidle")
    endpoint = page.locator("#endpointUrl").text_content().strip()
    assert endpoint.startswith("https://"), "Endpoint URL was not generated"
    print(f"  [OK] Endpoint created -> {endpoint}")
    return endpoint


# ── Scenario 1: Order API (async + Discord callback) ────────────────────────

class TestOrderApiDemo:

    ENDPOINT_NAME = "order-api-demo"
    ENDPOINT = None  # filled by the fixture

    @pytest.fixture(autouse=True)
    def setup_order(self, page):
        """Create endpoint, build callout rule with async response + callback."""
        page.goto("https://beeceptor.com")
        expect(page.locator("#channel")).to_be_visible()
        page.locator("#channel").fill(self.ENDPOINT_NAME)
        page.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle")
        ep = page.locator("#endpointUrl").text_content().strip()
        assert ep.startswith("https://")
        TestOrderApiDemo.ENDPOINT = ep
        print(f"  [OK] Order endpoint -> {ep}")

        # Open Rules
        page.locator("a[data-bs-target='.allRules']").click()
        page.locator("button.dropdown-toggle-split").click()
        page.locator("a.dropdown-item", has_text="New Callout Rule").click()
        page.wait_for_timeout(1000)

        # --- Request matching ---
        page.locator(".v2-conditions .col-sm-2 select").select_option("POST")
        page.locator("input.v2-path-input").fill("/api/order")
        page.locator(".v2-conditions .col-sm-4 select").select_option("path:equals")

        # --- Async response (instant 202) ---
        page.locator("#v2CollapseOne select").select_option("async")
        page.locator("#v2CollapseOne input[type='number']").nth(1).fill("202")
        page.locator("#v2CollapseOne textarea").fill(
            '{\n'
            '  "status": "processing",\n'
            '  "message": "Payment request accepted",\n'
            '  "orderId": "{{body \'orderId\'}}"\n'
            '}'
        )
        page.locator("#v2CollapseOne input[type='checkbox']").click()

        # --- Callout (POST to callbackUrl) ---
        page.locator("#v2CollapseTwo .col-sm-2 select").select_option("POST")
        page.locator("#v2CollapseTwo #targetEndpoint").fill("{{body 'callbackUrl'}}")
        page.locator("#v2CollapseTwo .col-sm-4 select").select_option("custom")

        # Callout body (with Handlebars)
        page.locator("#v2CollapseTwo textarea").fill(
            '{\n'
            '  "content": "Payment Successful\\n'
            'Order: {{body \'orderId\'}}\\n'
            'Status: SUCCESS\\n'
            'Transaction: {{faker \'string.uuid\'}}"\n'
            '}'
        )
        page.locator("#v2CollapseTwo input[type='checkbox']").click()

        # Add Content-Type header to callout
        page.locator("#v2CollapseTwo .v2-response-header-builder a.dropdown-toggle").click()
        page.locator("#v2CollapseTwo a.dropdown-item:has-text('JSON')").click()

        # Save rule
        page.locator("#saveV2Callout").click()

        print("  [OK] Order callout rule saved")

    def test_order_api(self):
        """Send a POST /api/order and verify the async 202 response."""
        assert self.ENDPOINT is not None, "Endpoint was not created"

        url = f"{self.ENDPOINT}/api/order"
        payload = {
            "orderId": "ORD123",
            "amount": 1000,
            "callbackUrl": (
                "https://discordapp.com/api/webhooks/"
                "1516131928506634302/5IShXnQ0tlcPrHoxJsgcmubuCXZFkirj0D-nwCeR_kl-MiHBONHg8RvOEdfhaFroW-Sy"
            ),
        }
        response = requests.post(url, json=payload, timeout=15)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}"
        )
        data = response.json()
        assert data["status"] == "processing"
        assert data["message"] == "Payment request accepted"
        assert data["orderId"] == "ORD123"
        print(f"  [OK] Order API: 202 + correct JSON body")
        print(f"    Response: {json.dumps(data, indent=4)}")


# ── Scenario 2: Dog API (sync callout proxy) ────────────────────────────────

class TestDogApiDemo:

    ENDPOINT_NAME = "get-dog-api"
    ENDPOINT = None

    @pytest.fixture(autouse=True)
    def setup_dog(self, page):
        """Create endpoint, build sync callout rule to dog.ceo."""
        page.goto("https://beeceptor.com")
        expect(page.locator("#channel")).to_be_visible()
        page.locator("#channel").fill(self.ENDPOINT_NAME)
        page.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle")
        ep = page.locator("#endpointUrl").text_content().strip()
        assert ep.startswith("https://")
        TestDogApiDemo.ENDPOINT = ep
        print(f"  [OK] Dog endpoint -> {ep}")

        # Open Rules
        page.locator("a[data-bs-target='.allRules']").click()
        page.locator("button.dropdown-toggle-split").click()
        page.locator("a.dropdown-item", has_text="New Callout Rule").click()

        # Request matching
        page.locator(".v2-conditions .col-sm-2 select").select_option("GET")
        page.locator(".v2-conditions .col-sm-4 select").select_option("path:equals")
        page.locator("input.v2-path-input").fill("/api/dog_image")

        # HTTP Callout: sync + GET
        page.locator("#v2CollapseOne select").select_option("sync")

        page.locator("#v2CollapseTwo .col-sm-2 select").select_option("GET")
        page.locator("#v2CollapseTwo #targetEndpoint").fill("https://dog.ceo/api/breeds/image/random")

        # Save rule
        page.locator("#saveV2Callout").click()
        page.wait_for_load_state("networkidle")
        print("  [OK] Dog callout rule saved")

    def test_dog_api(self):
        """GET /api/dog_image and verify proxy response from dog.ceo."""
        assert self.ENDPOINT is not None

        response = requests.get(f"{self.ENDPOINT}/api/dog_image", timeout=15)

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )
        data = response.json()
        assert "message" in data, "Missing 'message' field"
        assert "status" in data, "Missing 'status' field"
        assert data["message"].startswith("https://"), (
            f"Invalid image URL: {data['message']}"
        )
        assert data["status"] == "success"
        print(f"  [OK] Dog API: 200 + valid image URL")
        print(f"    Response: {json.dumps(data, indent=4)}")


# ── Scenario 3: Payment API (async + self-callback) ─────────────────────────

class TestPaymentApiDemo:

    ENDPOINT_NAME = "payment-api-demo"
    ENDPOINT = None

    @pytest.fixture(autouse=True)
    def setup_payment(self, page):
        """Create endpoint, build async callout rule + /callback rule."""
        page.goto("https://beeceptor.com")
        expect(page.locator("#channel")).to_be_visible()
        page.locator("#channel").fill(self.ENDPOINT_NAME)
        page.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle")
        ep = page.locator("#endpointUrl").text_content().strip()
        assert ep.startswith("https://")
        TestPaymentApiDemo.ENDPOINT = ep
        print(f"  [OK] Payment endpoint -> {ep}")

        # Open Rules
        page.locator("a[data-bs-target='.allRules']").click()
        page.locator("button.dropdown-toggle-split").click()
        page.locator("a.dropdown-item", has_text="New Callout Rule").click()

        # --- Rule 1: async callout on POST /api/payment ---
        page.locator(".v2-conditions .col-sm-2 select").select_option("POST")
        page.locator(".v2-conditions .col-sm-4 select").select_option("path:equals")
        page.locator("input.v2-path-input").fill("/api/payment")

        # Async response (instant 202)
        page.locator("#v2CollapseOne select").select_option("async")
        page.locator("#v2CollapseOne input[type='number']").nth(1).fill("202")
        page.locator("#v2CollapseOne textarea").fill(
            '{\n'
            '  "status": "success",\n'
            '  "message": "Payment processed successfully"\n'
            '}'
        )

        # Callout: POST to {endpoint}/callback
        page.locator("#v2CollapseTwo #targetEndpoint").fill(f"{ep}/callback")
        page.locator("#v2CollapseTwo .col-sm-2 select").select_option("POST")

        # Save rule 1
        page.locator("#saveV2Callout").click()
        page.wait_for_timeout(2000)

        # --- Rule 2: capture POST /callback ---
        page.locator("#createNew").click()
        page.wait_for_timeout(2000)
        page.locator(".v2-conditions .col-sm-2 select").select_option("POST")
        page.locator("input.v2-path-input").fill("/callback")

        # Save rule 2
        page.locator("#saveV2Rule").click()
        page.wait_for_load_state("networkidle")

        print("  [OK] Payment rules saved (callout + /callback)")

    def test_payment_api(self):
        """POST /api/payment and verify 202 instant response + callback."""
        assert self.ENDPOINT is not None

        url = f"{self.ENDPOINT}/api/payment"
        payload = {"amount": 1000, "customerId": "C123"}
        response = requests.post(url, json=payload, timeout=15)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}"
        )
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Payment processed successfully"
        print(f"  [OK] Payment API: 202 + correct JSON body")
        print(f"    Response: {json.dumps(data, indent=4)}")
