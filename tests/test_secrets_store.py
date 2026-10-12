import logging

from ave.secrets_store import cloud_preview, load_key, masked, save_key


def test_key_is_masked_and_roundtrips(tmp_path):
    db = tmp_path / "keys.sqlite"
    shown = save_key(db, "anthropic", "sk-ant-secretvalue1234")
    assert "secretvalue" not in shown
    assert shown.endswith("1234")
    assert load_key(db, "anthropic") == "sk-ant-secretvalue1234"
    assert masked(db, "anthropic") == shown


def test_key_never_appears_in_a_log_line(tmp_path, caplog):
    db = tmp_path / "keys.sqlite"
    secret = "sk-ant-secretvalue1234"
    with caplog.at_level(logging.INFO):
        shown = save_key(db, "anthropic", secret)
        logging.getLogger("ave").info("saved %s", shown)
    assert secret not in caplog.text


def test_cloud_preview_sends_text_only():
    preview = cloud_preview(transcripts=12, descriptions=40, tokens_in=18000, tokens_out=6000)
    assert "Video and audio" in preview["never"]
    assert "Transcripts" in preview["sent"]
    assert preview["estimated_cost"] > 0
