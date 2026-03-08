import pytest
from unittest.mock import patch, MagicMock
from notifier import FCMNotifier


def test_send_notification_returns_success():
    notifier = FCMNotifier(project_id="test-project", credentials=MagicMock())
    with patch("notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"name": "projects/test/messages/123"}
        result = notifier.send_one(
            token="device-token-abc",
            title="New Post",
            body="Check it out",
            link="https://example.com/post"
        )
    assert result["status"] == "sent"


def test_send_notification_handles_failure():
    notifier = FCMNotifier(project_id="test-project", credentials=MagicMock())
    with patch("notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"error": {"message": "INVALID_ARGUMENT"}}
        result = notifier.send_one(
            token="bad-token",
            title="New Post",
            body="Check it out",
            link="https://example.com/post"
        )
    assert result["status"] == "failed"
    assert "INVALID_ARGUMENT" in result["error_msg"]


def test_send_batch_returns_results_for_each():
    notifier = FCMNotifier(project_id="test-project", credentials=MagicMock())
    with patch.object(notifier, "send_one", return_value={"status": "sent"}) as mock_send:
        results = notifier.send_batch([
            {"token": "t1", "title": "A", "body": "b", "link": "https://a.com"},
            {"token": "t2", "title": "B", "body": "b", "link": "https://b.com"},
        ])
    assert len(results) == 2
    assert mock_send.call_count == 2
    assert all(r["status"] == "sent" for r in results)
