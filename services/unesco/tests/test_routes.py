# Tester för UNESCO routes
# Ansvarig: Sonia Tolouifar

import pytest
from app import app


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_sites_endpoint_returns_200(client):
    response = client.get("/api/sites")
    assert response.status_code == 200


def test_sites_endpoint_returns_list(client):
    response = client.get("/api/sites")
    data = response.get_json()
    assert isinstance(data, list)


def test_sites_radius_filter(client):
    response_small = client.get("/api/sites?radius=50")
    response_large = client.get("/api/sites?radius=150")
    assert len(response_small.get_json()) <= len(response_large.get_json())


def test_sites_category_filter(client):
    response = client.get("/api/sites?category=Cultural")
    data = response.get_json()
    assert all(s["category"] == "Cultural" for s in data)


def test_sites_category_filter_case_insensitive(client):
    response = client.get("/api/sites?category=cultural")
    data = response.get_json()
    assert all(s["category"] == "Cultural" for s in data)
