# Tester för UNESCO routes
# Ansvarig: Sonia Tolouifar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.unesco.routes import router

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


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


def test_chat_endpoint_returns_200(mocker):
    mocker.patch(
        "services.unesco.routes.chat_about_unesco",
        return_value="Gammelstaden är ett välbevarat medeltida stadscentrum.",
    )
    response = client.post(
        "/unesco/chat",
        json={"message": "Berätta om Gammelstaden"},
    )
    assert response.status_code == 200


def test_chat_endpoint_returns_answer_field(mocker):
    mocker.patch(
        "services.unesco.routes.chat_about_unesco",
        return_value="Gammelstaden är ett välbevarat medeltida stadscentrum.",
    )
    response = client.post(
        "/unesco/chat",
        json={"message": "Berätta om Gammelstaden"},
    )
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)


def test_chat_endpoint_with_custom_position(mocker):
    mocker.patch(
        "services.unesco.routes.chat_about_unesco",
        return_value="Drottningholms slott är ett världsarv nära Stockholm.",
    )
    response = client.post(
        "/unesco/chat",
        json={"message": "Vad finns nära mig?", "lat": 59.3293, "lon": 18.0686, "radius": 100},
    )
    assert response.status_code == 200
    assert response.json()["answer"] != ""


def test_chat_refuses_off_topic(mocker):
    mocker.patch(
        "services.unesco.routes.chat_about_unesco",
        return_value="Jag kan bara hjälpa till med frågor om UNESCO:s världsarv.",
    )
    response = client.post(
        "/unesco/chat",
        json={"message": "Vem är USA:s president?"},
    )
    assert response.status_code == 200
    assert "världsarv" in response.json()["answer"].lower()
