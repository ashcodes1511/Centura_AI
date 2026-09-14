from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal

client = TestClient(app)

def test_upload():
    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBjZW50dXJhLmFpIiwiZXhwIjoxNzg5NDA5NTk3fQ.cBVci8OAEaMz35Y31ZurIwb_xf6w3_rH_M5YeQs3rug'}
    )
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

if __name__ == "__main__":
    test_upload()
