import copy
from types import SimpleNamespace

import pytest
import requests

from ifncli.commands.whatsapp import WhatsAppRegisterTemplate
from ifncli.managers.whatsapp import WhatsAppTemplateError
from ifncli.managers.whatsapp_upload import (
    apply_placeholder_handles,
    find_header_handle_files,
    plan_uploads,
    resolve_header_handle_file,
    upload_header_handle,
    upload_header_handles,
)
from ifncli.platform import PlatformResources


# --- fakes for the HTTP layer --------------------------------------------------

class FakeResponse:
    def __init__(self, json_data=None, status_code=200, url=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.url = url
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                "%s Client Error: for url: %s" % (self.status_code, self.url), response=self)

    def json(self):
        if self._json_data is None:
            raise ValueError("no JSON body")
        return self._json_data


class FakePoster:
    """Records every call and returns the next response in the given order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, params=None, headers=None, data=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "data": data})
        return self.responses.pop(0)


# --- planning: find_header_handle_files ----------------------------------------

def test_find_header_handle_files_at_the_top_level():
    template = {"components": [
        {"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "media/banner.png"}},
        {"type": "BODY", "text": "hi"},
    ]}
    findings = find_header_handle_files(template)
    assert len(findings) == 1
    assert findings[0] == {"path": ("components", 0), "format": "IMAGE", "file": "media/banner.png"}


def test_find_header_handle_files_ignores_a_header_without_the_local_extension():
    template = {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::a"]}}]}
    assert find_header_handle_files(template) == []


def test_find_header_handle_files_inside_carousel_cards():
    template = {"components": [
        {"type": "BODY", "text": "hi"},
        {"type": "CAROUSEL", "cards": [
            {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "media/a.png"}}]},
            {"components": [{"type": "HEADER", "format": "VIDEO", "example": {"header_handle_file": "media/b.mp4"}}]},
        ]},
    ]}
    findings = find_header_handle_files(template)
    assert [(f["path"], f["file"]) for f in findings] == [
        (("components", 1, "cards", 0, "components", 0), "media/a.png"),
        (("components", 1, "cards", 1, "components", 0), "media/b.mp4"),
    ]


# --- planning: resolve_header_handle_file (path escape, MIME check) ------------

def test_resolve_accepts_a_file_inside_the_templates_root(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    (template_dir / "media").mkdir(parents=True)
    image = template_dir / "media" / "banner.png"
    image.write_bytes(b"fake-png")

    resolved, mime = resolve_header_handle_file("media/banner.png", template_dir, root, "IMAGE")
    assert resolved == image
    assert mime == "image/png"


def test_resolve_refuses_a_path_that_escapes_the_templates_root(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"fake-png")

    with pytest.raises(WhatsAppTemplateError, match="outside the templates folder"):
        resolve_header_handle_file("../../outside.png", template_dir, root, "IMAGE")


def test_resolve_refuses_a_symlink_that_escapes_the_templates_root(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it" / "media"
    template_dir.mkdir(parents=True)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"fake-png")
    link = template_dir / "banner.png"
    link.symlink_to(outside)

    with pytest.raises(WhatsAppTemplateError, match="outside the templates folder"):
        resolve_header_handle_file("banner.png", template_dir, root, "IMAGE")


@pytest.mark.parametrize("header_format,filename,expected_mime", [
    ("IMAGE", "a.jpg", "image/jpeg"),
    ("IMAGE", "a.jpeg", "image/jpeg"),
    ("IMAGE", "a.png", "image/png"),
    ("VIDEO", "a.mp4", "video/mp4"),
    ("GIF", "a.mp4", "video/mp4"),
    ("DOCUMENT", "a.pdf", "application/pdf"),
])
def test_resolve_accepts_every_documented_extension(tmp_path, header_format, filename, expected_mime):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    (template_dir / filename).write_bytes(b"data")

    _, mime = resolve_header_handle_file(filename, template_dir, root, header_format)
    assert mime == expected_mime


def test_resolve_rejects_an_extension_that_does_not_match_the_header_format(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    (template_dir / "a.gif").write_bytes(b"data")

    with pytest.raises(WhatsAppTemplateError, match="not valid for IMAGE"):
        resolve_header_handle_file("a.gif", template_dir, root, "IMAGE")


def test_resolve_rejects_header_handle_file_on_a_location_or_text_header(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    (template_dir / "a.png").write_bytes(b"data")

    with pytest.raises(WhatsAppTemplateError, match="not supported for HEADER format"):
        resolve_header_handle_file("a.png", template_dir, root, "LOCATION")


# --- plan_uploads: combines find + resolve --------------------------------------

def test_plan_uploads_returns_one_plan_per_finding(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    (template_dir / "banner.png").write_bytes(b"data")
    template_file = template_dir / "season_start.json"
    template = {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "banner.png"}},
                                {"type": "BODY", "text": "hi"}]}

    plans = plan_uploads(template, template_file, root)
    assert len(plans) == 1
    assert plans[0]["mime"] == "image/png"
    assert plans[0]["resolved"] == template_dir / "banner.png"


def test_plan_uploads_raises_on_the_first_invalid_finding(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    template_file = template_dir / "season_start.json"
    template = {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "../../etc/passwd"}}]}

    with pytest.raises(WhatsAppTemplateError):
        plan_uploads(template, template_file, root)


# --- apply_placeholder_handles (dry-run preview, pure) --------------------------

def test_apply_placeholder_handles_replaces_header_handle_file_with_a_placeholder():
    template = {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "banner.png"}}]}
    plans = [{"path": ("components", 0)}]

    updated = apply_placeholder_handles(template, plans, placeholder="PLACEHOLDER")
    assert updated["components"][0]["example"] == {"header_handle": ["PLACEHOLDER"]}
    # the original is untouched
    assert template["components"][0]["example"] == {"header_handle_file": "banner.png"}


# --- upload_header_handle: the two Resumable Upload steps -----------------------

def test_upload_header_handle_performs_exactly_two_requests(tmp_path):
    image = tmp_path / "banner.png"
    image.write_bytes(b"\x89PNG-fake-bytes")
    poster = FakePoster([
        FakeResponse(json_data={"id": "upload:ABC123"}),
        FakeResponse(json_data={"h": "4::aW...handle"}),
    ])

    handle = upload_header_handle(poster, "https://graph.facebook.com", "v26.0", "999", "SECRET_TOKEN", image, "image/png")

    assert handle == "4::aW...handle"
    assert len(poster.calls) == 2
    start_call, continue_call = poster.calls

    assert start_call["url"] == "https://graph.facebook.com/v26.0/999/uploads"
    assert start_call["params"] == {"file_name": "banner.png", "file_length": len(b"\x89PNG-fake-bytes"),
                                     "file_type": "image/png", "access_token": "SECRET_TOKEN"}
    assert start_call["headers"] is None
    assert start_call["data"] is None

    assert continue_call["url"] == "https://graph.facebook.com/v26.0/upload:ABC123"
    assert continue_call["headers"] == {"Authorization": "OAuth SECRET_TOKEN", "file_offset": "0"}
    assert continue_call["data"] == b"\x89PNG-fake-bytes"
    assert continue_call["params"] is None


def test_upload_header_handle_fails_cleanly_without_an_upload_session_id(tmp_path):
    image = tmp_path / "banner.png"
    image.write_bytes(b"data")
    poster = FakePoster([FakeResponse(json_data={})])

    with pytest.raises(WhatsAppTemplateError, match="upload session id"):
        upload_header_handle(poster, "https://graph.facebook.com", "v26.0", "999", "SECRET_TOKEN", image, "image/png")


# --- security: the access token never leaks on failure --------------------------

def test_upload_failure_never_leaks_the_access_token(tmp_path, capsys):
    image = tmp_path / "banner.png"
    image.write_bytes(b"data")
    token = "SECRET_TOKEN_XYZ"
    failing_url = "https://graph.facebook.com/v26.0/999/uploads?file_name=banner.png&access_token=%s" % token
    error_response = FakeResponse(status_code=400, url=failing_url,
                                   json_data={"error": {"code": 100, "message": "Invalid parameter"}})
    poster = FakePoster([error_response])

    with pytest.raises(WhatsAppTemplateError) as excinfo:
        upload_header_handle(poster, "https://graph.facebook.com", "v26.0", "999", token, image, "image/png")

    message = str(excinfo.value)
    assert token not in message
    assert "HTTP 400" in message and "100" in message and "Invalid parameter" in message

    out = capsys.readouterr().out
    assert token not in out


# --- upload_header_handles: app_id requirement and end-to-end replacement -------

def test_upload_header_handles_requires_app_id_only_when_a_template_needs_an_upload(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    template_file = template_dir / "t.json"
    template_without_media = {"components": [{"type": "BODY", "text": "hi"}]}

    # no app_id configured, but no upload is needed: no error, and the poster is never touched
    poster = FakePoster([])
    result = upload_header_handles(template_without_media, template_file, root, {"access_token": "t"}, poster=poster)
    assert result == template_without_media
    assert poster.calls == []


def test_upload_header_handles_raises_a_clear_error_when_app_id_is_missing(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    (template_dir / "banner.png").write_bytes(b"data")
    template_file = template_dir / "t.json"
    template = {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "banner.png"}}]}

    with pytest.raises(WhatsAppTemplateError, match="app_id"):
        upload_header_handles(template, template_file, root, {"access_token": "t"}, poster=FakePoster([]))


def test_upload_header_handles_returns_a_copy_with_real_handles(tmp_path):
    root = tmp_path / "whatsapp_templates"
    template_dir = root / "it"
    template_dir.mkdir(parents=True)
    (template_dir / "banner.png").write_bytes(b"data")
    template_file = template_dir / "t.json"
    template = {"components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "banner.png"}},
                                {"type": "BODY", "text": "hi"}]}
    original = copy.deepcopy(template)
    poster = FakePoster([FakeResponse(json_data={"id": "upload:1"}), FakeResponse(json_data={"h": "REAL_HANDLE"})])

    updated = upload_header_handles(template, template_file, root, {"access_token": "t", "app_id": "999"}, poster=poster)

    assert updated["components"][0]["example"] == {"header_handle": ["REAL_HANDLE"]}
    assert template == original  # the input template is never mutated


# --- dry-run at the command level: no HTTP call at all --------------------------

def run_register_template(tmp_path, monkeypatch, wa_config, argv, poster_calls_forbidden=True):
    templates_dir = tmp_path / "whatsapp_templates" / "it"
    templates_dir.mkdir(parents=True)
    (templates_dir / "media.png").write_bytes(b"data")
    template = {"name": "season_start_v1", "language": "it", "category": "MARKETING",
                "components": [{"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "media.png"}},
                                {"type": "BODY", "text": "Hello"}]}
    import json as json_module
    (templates_dir / "season_start_v1.json").write_text(json_module.dumps(template))

    if poster_calls_forbidden:
        def forbidden(*args, **kwargs):
            raise AssertionError("no HTTP call is expected during --dry-run")
        monkeypatch.setattr("ifncli.commands.whatsapp.requests.post", forbidden)
        monkeypatch.setattr("ifncli.managers.whatsapp_upload.requests.post", forbidden)

    manager = SimpleNamespace(get_platform=lambda: PlatformResources(tmp_path, None),
                               get_configs=lambda: {"whatsapp": wa_config})
    command = WhatsAppRegisterTemplate(SimpleNamespace(appConfigManager=manager), None)
    command.take_action(command.get_parser("ifn").parse_args([*argv, "season_start_v1"]))


def test_dry_run_plans_the_upload_and_makes_no_http_request(tmp_path, monkeypatch, capsys):
    run_register_template(tmp_path, monkeypatch, {"business_account_id": "1", "access_token": "t"},
                           ["--language", "it", "--dry-run"])
    out = capsys.readouterr().out
    assert "Would upload header media" in out
    assert "media.png" in out
    assert "<WOULD-BE-UPLOADED-HANDLE>" in out


def test_dry_run_does_not_require_app_id(tmp_path, monkeypatch, capsys):
    # app_id is only needed to actually upload; a preview must work without it.
    run_register_template(tmp_path, monkeypatch, {"business_account_id": "1", "access_token": "t"},
                           ["--language", "it", "--dry-run"])
    out = capsys.readouterr().out
    assert "app_id" not in out
