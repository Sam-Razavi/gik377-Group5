# Tester för UNESCO routes
# Ansvarig: Sonia Tolouifar

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_sites_endpoint_returns_200():
    response = client.get("/unesco/sites")
    assert response.status_code == 200


def test_sites_endpoint_returns_list():
    response = client.get("/unesco/sites")
    data = response.json()
    assert isinstance(data, list)


def test_sites_radius_filter():
    response_small = client.get("/unesco/sites?radius=50")
    response_large = client.get("/unesco/sites?radius=150")
    assert len(response_small.json()) <= len(response_large.json())


def test_sites_category_filter():
    response = client.get("/unesco/sites?category=Cultural")
    data = response.json()
    assert all(s["category"] == "Cultural" for s in data)


def test_sites_category_filter_case_insensitive():
    response = client.get("/unesco/sites?category=cultural")
    data = response.json()
    assert all(s["category"] == "Cultural" for s in data)


def test_sites_lat_lon_params():
    response = client.get("/unesco/sites?lat=59.3293&lon=18.0686&radius=50")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
