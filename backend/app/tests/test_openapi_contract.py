from fastapi.testclient import TestClient


def test_openapi_generation(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "ErrorResponse" in schema["components"]["schemas"]


def test_critical_endpoints_have_success_response_models(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    endpoints = {
        ("/api/v1/auth/login", "post"): "TokenResponse",
        ("/api/v1/medications", "get"): "MedicationResponse",
        ("/api/v1/schedules", "post"): "ScheduleResponse",
        ("/api/v1/dose-logs/{dose_log_id}/confirm", "patch"): "DoseLogResponse",
        ("/api/v1/caregivers/patients", "get"): "LinkedPatientResponse",
        ("/api/v1/uploads/signed-url", "post"): "SignedUploadResponse",
        ("/api/v1/devices", "post"): "DeviceResponse",
        ("/api/v1/privacy/export", "get"): "PrivacyExportResponse",
    }

    for (path, method), schema_name in endpoints.items():
        operation = schema["paths"][path][method]
        success = (
            operation["responses"]["200"]
            if "200" in operation["responses"]
            else operation["responses"]["201"]
        )
        encoded_success = str(success)
        assert schema_name in encoded_success


def test_standard_error_response_is_documented(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    login_responses = schema["paths"]["/api/v1/auth/login"]["post"]["responses"]
    assert login_responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }


def test_ai_endpoints_include_safety_message(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    scan_response = schema["components"]["schemas"]["ScanLabelResponse"]
    verify_response = schema["components"]["schemas"]["VerifyMedicationResponse"]

    assert "safety_message" in scan_response["properties"]
    assert "safety_message" in verify_response["properties"]
