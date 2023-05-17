"""Test ingress API."""
import asyncio
from unittest.mock import patch

import pytest

# pylint: disable=redefined-outer-name


@pytest.mark.asyncio
async def test_validate_session(api_client, coresys):
    """Test validating ingress session."""
    with patch("aiohttp.web_request.BaseRequest.__getitem__", return_value=None):
        resp = await api_client.post(
            "/ingress/validate_session",
            json={"session": "non-existing"},
        )
        assert resp.status == 401

    with patch(
        "aiohttp.web_request.BaseRequest.__getitem__",
        return_value=coresys.homeassistant,
    ):
        resp = await api_client.post("/ingress/session")
        result = await resp.json()

        assert "session" in result["data"]
        session = result["data"]["session"]
        assert session in coresys.ingress.sessions

        valid_time = coresys.ingress.sessions[session]

        resp = await api_client.post(
            "/ingress/validate_session",
            json={"session": session},
        )
        assert resp.status == 200
        assert await resp.json() == {"result": "ok", "data": {}}

        assert coresys.ingress.sessions[session] > valid_time


@pytest.mark.asyncio
async def test_validate_session_with_user_id(api_client, coresys):
    """Test validating ingress session with user ID passed."""
    with patch("aiohttp.web_request.BaseRequest.__getitem__", return_value=None):
        resp = await api_client.post(
            "/ingress/validate_session",
            json={"session": "non-existing"},
        )
        assert resp.status == 401

    with patch(
        "aiohttp.web_request.BaseRequest.__getitem__",
        return_value=coresys.homeassistant,
    ):
        client = coresys.homeassistant.websocket._client

        create_session_result = asyncio.Future()
        client.async_send_command.return_value = create_session_result

        create_session_request = api_client.post(
            "/ingress/session", json={"user_id": "some-id"}
        )
        create_session_result.set_result(
            [{"id": "some-id", "name": "Some Name", "username": "sn"}]
        )
        create_session_result.done()

        resp = await create_session_request
        result = await resp.json()

        client.async_send_command.assert_called_with({"type": "config/auth/list"})

        assert "session" in result["data"]
        session = result["data"]["session"]
        assert session in coresys.ingress.sessions

        valid_time = coresys.ingress.sessions[session]

        resp = await api_client.post(
            "/ingress/validate_session",
            json={"session": session},
        )
        assert resp.status == 200
        assert await resp.json() == {"result": "ok", "data": {}}

        assert coresys.ingress.sessions[session] > valid_time
        assert coresys.ingress.sessions_data[session]["user"]["id"] == "some-id"
        assert coresys.ingress.sessions_data[session]["user"]["username"] == "sn"
        assert (
            coresys.ingress.sessions_data[session]["user"]["display_name"]
            == "Some Name"
        )
