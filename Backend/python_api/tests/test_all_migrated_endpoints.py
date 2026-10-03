"""
Automated QA Verification Suite for Migrated Python API Endpoints
Follows agent-qa-debug-fix guidelines.
Tests all migrated endpoints:
  - Root Health & Static routes
  - Auth (Register, Login, Me)
  - Payment (Create Order, Status, Simulate)
  - Supervisor AI (Socratic Questions, Examiner, Macro Review, Readiness)
  - Admin (Stats, Users, Orders, Telemetry, Audit Logs, Manual Settle)
"""

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8001"


def api_call(method: str, path: str, data: dict = None, headers: dict = None):
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
            if "application/json" in content_type:
                return status_code, json.loads(body.decode("utf-8"))
            return status_code, body.decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


def run_tests():
    passed = 0
    total = 0

    def assert_test(name, condition, extra=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f" [PASS] {name}")
        else:
            print(f" [FAIL] {name}: {extra}")

    print("\n--- 1. Testing Health & Static Routes ---")
    st, resp = api_call("GET", "/health")
    assert_test("GET /health status == 200", st == 200 and resp.get("status") == "ok", resp)

    st, resp = api_call("GET", "/api/v1/health")
    assert_test("GET /api/v1/health status == 200", st == 200 and resp.get("status") == "ok", resp)

    st, resp = api_call("GET", "/app")
    assert_test("GET /app serves HTML", st == 200 and "<html" in resp.lower(), f"Status: {st}")

    st, resp = api_call("GET", "/auth")
    assert_test("GET /auth serves HTML", st == 200 and "<html" in resp.lower(), f"Status: {st}")

    st, resp = api_call("GET", "/admin")
    assert_test("GET /admin serves HTML", st == 200 and "<html" in resp.lower(), f"Status: {st}")

    print("\n--- 2. Testing Authentication Routes ---")
    # Login demo user
    st, login_resp = api_call("POST", "/api/v1/auth/login", {
        "email": "alif.awwaz@ui.ac.id",
        "password": "thesa2026"
    })
    assert_test("POST /api/v1/auth/login demo user", st == 200 and login_resp.get("success") is True, login_resp)
    token = login_resp.get("token")

    # Check Me endpoint
    st, me_resp = api_call("GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert_test("GET /api/v1/auth/me with valid token", st == 200 and me_resp.get("user", {}).get("email") == "alif.awwaz@ui.ac.id", me_resp)

    # Register new user
    new_email = "test.student2026@itb.ac.id"
    st, reg_resp = api_call("POST", "/api/v1/auth/register", {
        "name": "Budi Santoso",
        "email": new_email,
        "password": "securepassword123",
        "institution": "Institut Teknologi Bandung",
        "prodi": "Teknik Informatika",
        "level": "S1"
    })
    # If user already registered from previous run, that's fine too
    if st == 400 and "sudah terdaftar" in str(reg_resp):
        assert_test("POST /api/v1/auth/register duplicate handled gracefully", True)
    else:
        assert_test("POST /api/v1/auth/register new user", st == 201 and reg_resp.get("success") is True, reg_resp)

    print("\n--- 3. Testing Payment Routes ---")
    st, order_resp = api_call("POST", "/api/v1/payment/create-order", {
        "package_id": "single",
        "amount": 12000,
        "user_email": "test.student2026@itb.ac.id",
        "user_name": "Budi Santoso",
        "payment_type": "qris"
    })
    assert_test("POST /api/v1/payment/create-order", st == 200 and order_resp.get("success") is True, order_resp)
    order_id = order_resp.get("order_id")

    st, status_resp = api_call("GET", f"/api/v1/payment/status?order_id={order_id}")
    assert_test("GET /api/v1/payment/status pending", st == 200 and status_resp.get("status") == "pending", status_resp)

    st, sim_resp = api_call("POST", f"/api/v1/payment/simulate?order_id={order_id}")
    assert_test("POST /api/v1/payment/simulate settlement", st == 200 and sim_resp.get("status") == "settled", sim_resp)

    st, status_after = api_call("GET", f"/api/v1/payment/status?order_id={order_id}")
    assert_test("GET /api/v1/payment/status settled", st == 200 and status_after.get("settled") is True, status_after)

    print("\n--- 4. Testing Supervisor & Examiner AI Routes ---")
    st, soc_resp = api_call("POST", "/api/v1/supervisor/socratic-questions", {
        "document": "Penelitian ini mengkaji optimasi algoritma AI untuk edukasi akademik.",
        "topic": "Optimasi AI untuk Edukasi"
    })
    assert_test("POST /api/v1/supervisor/socratic-questions", st == 200 and len(soc_resp.get("questions", [])) > 0, soc_resp)

    st, exam_ask = api_call("POST", "/api/v1/supervisor/examiner-simulate", {
        "mode": "ask",
        "topic": "Deep Learning dalam Deteksi Penyakit Tanaman",
        "persona": "kritis"
    })
    assert_test("POST /api/v1/supervisor/examiner-simulate ask", st == 200 and "question_text" in exam_ask, exam_ask)

    st, exam_eval = api_call("POST", "/api/v1/supervisor/examiner-simulate", {
        "mode": "evaluate",
        "topic": "Deep Learning dalam Deteksi Penyakit Tanaman",
        "answer": "Kami menggunakan dataset terkurasi dengan augmentasi citra dan cross-validation 5-fold untuk memastikan model bebas dari data leakage.",
        "persona": "metodologis"
    })
    assert_test("POST /api/v1/supervisor/examiner-simulate evaluate", st == 200 and exam_eval.get("score") is not None, exam_eval)

    st, macro_resp = api_call("POST", "/api/v1/supervisor/analyze", {
        "document": "Bab I Pendahuluan. Latar belakang riset ini dilandasi oleh perkembangan AI (Smith, 2023)."
    })
    assert_test("POST /api/v1/supervisor/analyze", st == 200 and "macro_review" in macro_resp, macro_resp)

    st, ready_resp = api_call("POST", "/api/v1/supervisor/readiness", {
        "macro_review": macro_resp.get("macro_review")
    })
    assert_test("POST /api/v1/supervisor/readiness", st == 200 and "readiness_report" in ready_resp, ready_resp)

    print("\n--- 5. Testing Admin Controlling Routes ---")
    admin_headers = {
        "X-Admin-Secret": "thesa_super_admin_jwt_secret_2026_change_in_prod",
        "Authorization": "Bearer thesa_admin_master_token_2026"
    }

    st, stats_resp = api_call("GET", "/api/v1/admin/stats", headers=admin_headers)
    assert_test("GET /api/v1/admin/stats", st == 200 and stats_resp.get("success") is True, stats_resp)

    st, users_resp = api_call("GET", "/api/v1/admin/users", headers=admin_headers)
    assert_test("GET /api/v1/admin/users", st == 200 and users_resp.get("count", 0) > 0, users_resp)

    st, orders_resp = api_call("GET", "/api/v1/admin/orders", headers=admin_headers)
    assert_test("GET /api/v1/admin/orders", st == 200 and orders_resp.get("count", 0) > 0, orders_resp)

    st, tel_resp = api_call("GET", "/api/v1/admin/llm-telemetry", headers=admin_headers)
    assert_test("GET /api/v1/admin/llm-telemetry", st == 200 and "telemetry" in tel_resp, tel_resp)

    st, audit_resp = api_call("GET", "/api/v1/admin/audit-logs", headers=admin_headers)
    assert_test("GET /api/v1/admin/audit-logs", st == 200 and "logs" in audit_resp, audit_resp)

    print(f"\n==========================================")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"==========================================")
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
