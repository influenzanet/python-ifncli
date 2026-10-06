import copy
from types import SimpleNamespace

import pytest
import yaml

from ifncli.commands import whatsapp_link
from ifncli.commands.whatsapp_link import WhatsAppLinkTemplate
from ifncli.managers.whatsapp import WhatsAppTemplateError, read_template_binding
from ifncli.platform import PlatformResources

BINDINGS = """study-reminder:
  template: "study_reminder_v1"
  params:
    button_0: "loginToken"
"""

BOTH = {"it": "APPROVED", "en": "APPROVED"}


def stored_reminder(study_key="influweb", subject="s"):
    return {"id": "65f0c0ffee0000000000abcd", "messageType": "study-reminder", "studyKey": study_key,
            "defaultLanguage": "it",
            "headerOverrides": {"from": "noreply@example.org", "replyTo": ["help@example.org"]},
            "translations": [{"lang": "it", "subject": subject, "templateDef": "PGh0bWw+"},
                             {"lang": "en", "subject": subject, "templateDef": "PGh0bWw+"}]}


class FakeClient:
    """Management API holding e-mail templates; `later` replaces them from the second read on."""

    def __init__(self, first, later=None):
        self.reads = [first, later if later is not None else first]
        self.gets = 0
        self.saved = []

    def get_all_templates(self):
        templates = self.reads[min(self.gets, 1)]
        self.gets += 1
        if self.saved:
            templates = [self.saved[-1]]
        return {"templates": copy.deepcopy(templates)}

    def save_email_template(self, template_object):
        self.saved.append(copy.deepcopy(template_object))
        return copy.deepcopy(template_object)


def run(tmp_path, monkeypatch, client, statuses=None, argv=(), bindings=BINDINGS, name="study-reminder"):
    folder = tmp_path / "email_templates"
    folder.mkdir(exist_ok=True)
    if bindings is not None:
        (folder / "whatsapp.yaml").write_text(bindings)
    meta_calls = []

    def fake_statuses(wa_config, template_name):
        meta_calls.append(template_name)
        return statuses or {}
    monkeypatch.setattr(whatsapp_link, "fetch_template_statuses", fake_statuses)
    manager = SimpleNamespace(get_platform=lambda: PlatformResources(tmp_path, None),
                              get_management_api=lambda: client,
                              get_configs=lambda: {"whatsapp": {"business_account_id": "1", "access_token": "t"}})
    command = WhatsAppLinkTemplate(SimpleNamespace(appConfigManager=manager), None)
    command.take_action(command.get_parser("ifn").parse_args([*argv, name]))
    return meta_calls


def test_link_saves_the_stored_template_with_the_binding_only(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder()])
    meta_calls = run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert meta_calls == ["study_reminder_v1"]
    assert len(client.saved) == 1
    expected = stored_reminder()
    expected["whatsappTemplateName"] = "study_reminder_v1"
    expected["whatsappParams"] = {"button_0": "loginToken"}
    assert client.saved[0] == expected


def test_link_picks_the_template_of_the_given_study(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder("other"), stored_reminder("influweb")])
    run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert client.saved[0]["studyKey"] == "influweb"


def test_link_refuses_a_template_not_approved_in_a_language_of_the_stored_template(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder()])
    with pytest.raises(WhatsAppTemplateError, match=r"en \(PENDING\)"):
        run(tmp_path, monkeypatch, client, {"it": "APPROVED", "en": "PENDING"}, ["--study", "influweb"])
    assert client.saved == []


def test_languages_narrows_the_approval_check(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder()])
    run(tmp_path, monkeypatch, client, {"it": "APPROVED", "en": "PENDING"}, ["--study", "influweb", "--languages", "it"])
    assert len(client.saved) == 1


def test_link_refuses_a_system_message(tmp_path, monkeypatch):
    client = FakeClient([])
    bindings = BINDINGS + 'registration:\n  template: "x"\n'
    with pytest.raises(WhatsAppTemplateError, match="system message"):
        run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"], bindings=bindings, name="registration")
    assert client.gets == 0 and client.saved == []


def test_link_requires_a_study(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder()])
    with pytest.raises(WhatsAppTemplateError, match="--study is required"):
        run(tmp_path, monkeypatch, client, BOTH)
    assert client.gets == 0 and client.saved == []


def test_link_refuses_a_template_that_is_not_on_the_platform(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder("other")])
    with pytest.raises(WhatsAppTemplateError, match="email:import-template"):
        run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert client.saved == []


def test_link_saves_nothing_when_the_template_changed_after_it_was_read(tmp_path, monkeypatch):
    # someone imported the e-mail again between the read and the save
    client = FakeClient([stored_reminder()], [stored_reminder(subject="new subject")])
    with pytest.raises(WhatsAppTemplateError, match="changed while it was being bound"):
        run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert client.saved == []


def test_dry_run_saves_nothing(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder()])
    run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb", "--dry-run"])
    assert client.saved == []


def test_unlink_sends_an_empty_name_without_asking_meta(tmp_path, monkeypatch):
    linked = stored_reminder()
    linked.update(whatsappTemplateName="study_reminder_v1", whatsappParams={"button_0": "loginToken"})
    client = FakeClient([linked])
    meta_calls = run(tmp_path, monkeypatch, client, None, ["--study", "influweb", "--unlink"], bindings=None)
    assert meta_calls == []
    assert client.saved[0]["whatsappTemplateName"] == "" and "whatsappParams" not in client.saved[0]


def test_email_template_folder_option_is_used(tmp_path, monkeypatch):
    other = tmp_path / "study_emails"
    other.mkdir()
    (other / "whatsapp.yaml").write_text(BINDINGS)
    client = FakeClient([stored_reminder()])
    run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb", "--email_template_folder", str(other)], bindings=None)
    assert client.saved[0]["whatsappTemplateName"] == "study_reminder_v1"


def test_missing_bindings_file_is_a_clear_error(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder()])
    with pytest.raises(WhatsAppTemplateError, match="whatsapp.yaml"):
        run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"], bindings=None)


def test_read_template_binding_needs_an_entry_for_the_message_type():
    with pytest.raises(WhatsAppTemplateError, match="no entry for 'newsletter'"):
        read_template_binding(yaml.safe_load(BINDINGS), "newsletter")


def test_read_template_binding_rejects_a_malformed_entry():
    with pytest.raises(WhatsAppTemplateError, match="whatsapp.template"):
        read_template_binding({"study-reminder": {"template": ""}}, "study-reminder")


def test_read_template_binding_returns_name_and_params():
    assert read_template_binding(yaml.safe_load(BINDINGS), "study-reminder") == ("study_reminder_v1", {"button_0": "loginToken"})


def test_link_is_not_stopped_by_translations_read_back_in_another_order(tmp_path, monkeypatch):
    reordered = stored_reminder()
    reordered["translations"].reverse()
    client = FakeClient([stored_reminder()], [reordered])
    run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert len(client.saved) == 1


def test_link_refuses_two_stored_templates_with_the_same_type_and_study(tmp_path, monkeypatch):
    client = FakeClient([stored_reminder(), stored_reminder()])
    with pytest.raises(WhatsAppTemplateError, match="2 e-mail templates"):
        run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert client.saved == []


def test_link_refuses_a_stored_template_without_translations(tmp_path, monkeypatch):
    empty = stored_reminder()
    empty["translations"] = []
    client = FakeClient([empty])
    with pytest.raises(WhatsAppTemplateError, match="no translations"):
        run(tmp_path, monkeypatch, client, BOTH, ["--study", "influweb"])
    assert client.saved == []


def test_read_template_binding_explains_an_entry_that_is_not_a_mapping():
    with pytest.raises(WhatsAppTemplateError, match="'study-reminder' in whatsapp.yaml must be"):
        read_template_binding({"study-reminder": "study_reminder_v1"}, "study-reminder")
