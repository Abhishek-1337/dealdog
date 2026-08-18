from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_search_and_track_flow():
    with TestClient(app) as client:
        resp = client.get("/api/search", params={"q": "macbook m3"})
        assert resp.status_code == 200
        groups = resp.json()["groups"]
        assert groups

        eight = next(
            g for g in groups if g["attributes"].get("ram") == "8GB" and g["attributes"].get("storage") == "256GB"
        )
        track = client.post(
            "/api/track",
            json={"attributes": eight["attributes"], "listings": eight["listings"], "product_id": None},
        )
        assert track.status_code == 200
        product_id = track.json()["product_id"]

        tracked = client.get("/api/tracked")
        assert tracked.status_code == 200
        assert any(t["product_id"] == product_id for t in tracked.json())

        detail = client.get(f"/api/products/{product_id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == product_id
        assert len(detail.json()["history"]) >= 1
