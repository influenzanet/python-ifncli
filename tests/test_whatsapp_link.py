import copy
import time
from types import SimpleNamespace

import pytest

from ifncli.commands import whatsapp_link
from ifncli.commands.whatsapp_link import WhatsAppLinkAutoMessage
from ifncli.managers.whatsapp import WhatsAppTemplateError
from ifncli.platform import PlatformResources

SETTINGS = """sendTo: "all-users"
studyKey: "influweb"
messageType: "weekly"
period: 86400
defaultLanguage: "it"
translations:
  - lang: "en"
    subject: "s"
    templateFile: "en.html"
  - lang: "it"
    subject: "s"
    templateFile: "it.html"
whatsapp:
  template: "weekly_reminder_v2"
  params:
    button_0: "loginToken"
"""


def stored_weekly(next_time):
    return {"id": "6927255194ad2b74d2149f48", "type": "all-users", "studyKey": "influweb",
            "nextTime": str(next_time), "period": "86400", "condition": {"dtype": "num", "num": 1},
            "template": {"id": "000000000000000000000000", "messageType": "weekly", "defaultLanguage": "it",
                         "translations": [{"lang": "it", "subject": "s", "templateDef": "PGh0bWw+"}]}}


class FakeClient:
    """Management API returning the weekly; `later` is what a second read returns."""

    def __init__(self, first, later=None):
        self.reads = [first, later or first]
        self.gets = 0
        self.saved = []

    def get_auto_messages(self):
        message = self.reads[min(self.gets, 1)]
        self.gets += 1
        if self.saved:
            message = self.saved[-1]["autoMessage"]
        return {"autoMessages": [copy.deepcopy(message)]}

    def save_auto_message(self, payload):
        self.saved.append(copy.deepcopy(payload))


def run(tmp_path, monkeypatch, client, statuses=None, argv=()):
    folder = tmp_path / "auto_messages" / "weekly_reminder"
    folder.mkdir(parents=True)
    (folder / "settings.yaml").write_text(SETTINGS)
    meta_calls = []

    def fake_statuses(wa_config, name):
        meta_calls.append(name)
        return statuses or {}
    monkeypatch.setattr(whatsapp_link, "fetch_template_statuses", fake_statuses)
    manager = SimpleNamespace(get_platform=lambda: PlatformResources(tmp_path, None),
                              get_management_api=lambda: client,
                              get_configs=lambda: {"whatsapp": {"business_account_id": "1", "access_token": "t"}})
    command = WhatsAppLinkAutoMessage(SimpleNamespace(appConfigManager=manager), None)
    command.take_action(command.get_parser("ifn").parse_args([*argv, "weekly_reminder"]))
    return meta_calls


FAR = int(time.time()) + 86400
BOTH = {"it": "APPROVED", "en": "APPROVED"}


def test_link_saves_the_stored_message_with_the_binding_only(tmp_path, monkeypatch):
    client = FakeClient(stored_weekly(FAR))
    run(tmp_path, monkeypatch, client, BOTH)
    assert len(client.saved) == 1
    sent = client.saved[0]["autoMessage"]
    expected = stored_weekly(FAR)
    expected["template"]["whatsappTemplateName"] = "weekly_reminder_v2"
    expected["template"]["whatsappParams"] = {"button_0": "loginToken"}
    assert sent == expected


def test_link_refuses_a_template_not_approved_in_a_language_of_the_message(tmp_path, monkeypatch):
    client = FakeClient(stored_weekly(FAR))
    with pytest.raises(WhatsAppTemplateError, match=r"en \(PENDING\)"):
        run(tmp_path, monkeypatch, client, {"it": "APPROVED", "en": "PENDING"})
    assert client.saved == [] and client.gets == 0


def test_languages_narrows_the_approval_check(tmp_path, monkeypatch):
    client = FakeClient(stored_weekly(FAR))
    run(tmp_path, monkeypatch, client, {"it": "APPROVED", "en": "PENDING"}, ["--languages", "it"])
    assert len(client.saved) == 1


def test_link_refuses_a_message_due_within_the_margin(tmp_path, monkeypatch):
    client = FakeClient(stored_weekly(int(time.time()) + 300))
    with pytest.raises(WhatsAppTemplateError, match="due within 10 minutes"):
        run(tmp_path, monkeypatch, client, BOTH)
    assert client.saved == []


def test_link_saves_nothing_when_the_message_changed_after_it_was_read(tmp_path, monkeypatch):
    # the scheduler ran between the read and the save and moved nextTime forward
    client = FakeClient(stored_weekly(FAR), stored_weekly(FAR + 86400))
    with pytest.raises(WhatsAppTemplateError, match="changed while it was being bound"):
        run(tmp_path, monkeypatch, client, BOTH)
    assert client.saved == []


def test_dry_run_saves_nothing(tmp_path, monkeypatch):
    client = FakeClient(stored_weekly(FAR))
    run(tmp_path, monkeypatch, client, BOTH, ["--dry-run"])
    assert client.saved == []


def test_unlink_sends_an_empty_name_without_asking_meta(tmp_path, monkeypatch):
    linked = stored_weekly(FAR)
    linked["template"].update(whatsappTemplateName="weekly_reminder_v2", whatsappParams={"button_0": "loginToken"})
    client = FakeClient(linked)
    meta_calls = run(tmp_path, monkeypatch, client, None, ["--unlink"])
    assert meta_calls == []
    template = client.saved[0]["autoMessage"]["template"]
    assert template["whatsappTemplateName"] == "" and "whatsappParams" not in template


def test_link_refuses_a_message_that_is_not_on_the_platform(tmp_path, monkeypatch):
    other = stored_weekly(FAR)
    other["studyKey"] = "italy"
    client = FakeClient(other)
    with pytest.raises(WhatsAppTemplateError, match="not found on the platform"):
        run(tmp_path, monkeypatch, client, BOTH)
