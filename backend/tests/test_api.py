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
        assert len(detail.json()["price_history"]["records"]) >= 1


def test_history_endpoint_grows_on_refresh():
    with TestClient(app) as client:
        groups = client.get("/api/search", params={"q": "iphone 15 128gb"}).json()["groups"]
        listings = groups[0]["listings"]
        product_id = client.post(
            "/api/track",
            json={"attributes": groups[0]["attributes"], "listings": listings, "product_id": None},
        ).json()["product_id"]

        first = client.get(f"/api/products/{product_id}/history")
        assert first.status_code == 200
        body = first.json()
        assert body["product_id"] == product_id
        assert len(body["sites"]) == len({item["site"] for item in listings})
        assert body["best_price"] == min(item["price"] for item in listings)

        refreshed = client.post(f"/api/products/{product_id}/history").json()
        assert len(refreshed["records"]) > len(body["records"]), "a scrape round appends rows"
        # Nothing from the first round was rewritten.
        assert refreshed["records"][: len(body["records"])] == body["records"]


def test_history_endpoint_404s_for_unknown_product():
    with TestClient(app) as client:
        assert client.get("/api/products/99999/history").status_code == 404
        assert client.post("/api/products/99999/history").status_code == 404
