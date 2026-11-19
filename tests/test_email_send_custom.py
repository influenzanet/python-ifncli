import copy
from types import SimpleNamespace

import pytest

from ifncli.commands import whatsapp_link
from ifncli.commands.email import SendCustom
from ifncli.managers.whatsapp import WhatsAppTemplateError

SETTINGS = """sendTo: "study-participants"
studyKey: "influweb"
messageType: "newsletter"
defaultLanguage: "it"
translations:
  - lang: "en"
    subject: "Welcome back"
    templateFile: "en.html"
  - lang: "it"
    subject: "Bentornati"
    templateFile: "it.html"
"""


def whatsapp(**params):
    section = 'whatsapp:\n  template: "season_start_v2"\n'
    if params:
        section += "  params:\n" + "".join('    %s: "%s"\n' % item for item in params.items())
    return section


# A newsletter on WhatsApp needs its unsubscribe button.
WHATSAPP = whatsapp(button_1="unsubscribeToken")

BOTH = {"it": "APPROVED", "en": "APPROVED"}


class FakeClient:
    """Management API recording the send requests."""

    def __init__(self):
        self.all_users = []
        self.participants = []

    def send_message_to_all_users(self, template_object, ignore_weekday=False):
        self.all_users.append((copy.deepcopy(template_object), ignore_weekday))

    def send_message_to_study_participants(self, study_key, condition, template_object, ignore_weekday=False):
        self.participants.append((study_key, copy.deepcopy(condition), copy.deepcopy(template_object), ignore_weekday))


def run(tmp_path, monkeypatch, client, settings=SETTINGS, statuses=None, argv=(), meta_calls=None):
    folder = tmp_path / "season_start_email"
    folder.mkdir(exist_ok=True)
    (folder / "settings.yaml").write_text(settings)
    (folder / "it.html").write_text("<p>ciao</p>")
    (folder / "en.html").write_text("<p>hello</p>")
    meta_calls = [] if meta_calls is None else meta_calls

    def fake_statuses(wa_config, name):
        meta_calls.append(name)
        return statuses or {}
    monkeypatch.setattr(whatsapp_link, "fetch_template_statuses", fake_statuses)
    manager = SimpleNamespace(get_management_api=lambda: client,
                              get_configs=lambda: {"whatsapp": {"business_account_id": "1", "access_token": "t"}})
    command = SendCustom(SimpleNamespace(appConfigManager=manager), None)
    command.take_action(command.get_parser("ifn").parse_args(["--email_folder", str(folder), *argv]))
    return meta_calls


def test_without_whatsapp_the_request_to_all_users_is_unchanged(tmp_path, monkeypatch):
    client = FakeClient()
    meta_calls = run(tmp_path, monkeypatch, client)
    assert meta_calls == []
    assert len(client.all_users) == 1 and client.participants == []
    template, ignore_weekday = client.all_users[0]
    assert set(template) == {"messageType", "defaultLanguage", "translations"}
    assert template["messageType"] == "newsletter" and ignore_weekday is False


def test_without_whatsapp_the_request_to_study_participants_is_unchanged(tmp_path, monkeypatch):
    client = FakeClient()
    run(tmp_path, monkeypatch, client, argv=["--study_key", "influweb"])
    study_key, condition, template, ignore_weekday = client.participants[0]
    assert study_key == "influweb" and condition == {"dtype": "num", "num": 1}
    assert "whatsappTemplateName" not in template and ignore_weekday is False


def test_whatsapp_section_is_sent_with_the_message(tmp_path, monkeypatch):
    client = FakeClient()
    meta_calls = run(tmp_path, monkeypatch, client, SETTINGS + WHATSAPP, BOTH, ["--study_key", "influweb"])
    assert meta_calls == ["season_start_v2"]
    template = client.participants[0][2]
    assert template["whatsappTemplateName"] == "season_start_v2"
    assert template["whatsappParams"] == {"button_1": "unsubscribeToken"}


def test_whatsapp_params_are_sent(tmp_path, monkeypatch):
    client = FakeClient()
    settings = SETTINGS.replace('"newsletter"', '"study-reminder"') + whatsapp(button_0="loginToken")
    run(tmp_path, monkeypatch, client, settings, BOTH)
    assert client.all_users[0][0]["whatsappParams"] == {"button_0": "loginToken"}


def test_nothing_is_sent_when_the_template_is_not_approved_in_a_language(tmp_path, monkeypatch):
    client = FakeClient()
    with pytest.raises(WhatsAppTemplateError, match=r"en \(PENDING\)"):
        run(tmp_path, monkeypatch, client, SETTINGS + WHATSAPP, {"it": "APPROVED", "en": "PENDING"})
    assert client.all_users == [] and client.participants == []


def test_a_login_param_on_a_send_to_all_users_without_login_token_is_refused(tmp_path, monkeypatch):
    client = FakeClient()
    meta_calls = []
    settings = SETTINGS + whatsapp(button_0="loginToken", button_1="unsubscribeToken")
    with pytest.raises(WhatsAppTemplateError, match="button_0 use loginToken/loginUrl, which a 'newsletter' message sent to all-users does not get"):
        run(tmp_path, monkeypatch, client, settings, BOTH, meta_calls=meta_calls)
    assert client.all_users == [] and meta_calls == []


def test_a_login_param_on_a_study_send_is_accepted(tmp_path, monkeypatch):
    # A send to study participants always gets a login token, whatever the message type.
    client = FakeClient()
    settings = SETTINGS + whatsapp(button_0="loginToken", button_1="unsubscribeToken")
    run(tmp_path, monkeypatch, client, settings, BOTH, ["--study_key", "influweb"])
    template = client.participants[0][2]
    assert template["whatsappParams"] == {"button_0": "loginToken", "button_1": "unsubscribeToken"}


@pytest.mark.parametrize("argv", [(), ("--study_key", "influweb")])
def test_a_newsletter_without_an_unsubscribe_param_is_refused(tmp_path, monkeypatch, argv):
    client = FakeClient()
    meta_calls = []
    with pytest.raises(WhatsAppTemplateError, match="needs a parameter filled from unsubscribeToken"):
        run(tmp_path, monkeypatch, client, SETTINGS + whatsapp(), BOTH, argv, meta_calls=meta_calls)
    assert client.all_users == [] and client.participants == [] and meta_calls == []


def test_an_unsubscribe_param_on_another_message_type_is_refused(tmp_path, monkeypatch):
    client = FakeClient()
    settings = SETTINGS.replace('"newsletter"', '"study-reminder"') + WHATSAPP
    with pytest.raises(WhatsAppTemplateError, match="button_1 use unsubscribeToken, which only newsletter messages get"):
        run(tmp_path, monkeypatch, client, settings, BOTH, ["--study_key", "influweb"])
    assert client.participants == []


def test_dry_run_sends_nothing(tmp_path, monkeypatch):
    client = FakeClient()
    meta_calls = run(tmp_path, monkeypatch, client, SETTINGS + WHATSAPP, BOTH, ["--dry-run"])
    assert meta_calls == ["season_start_v2"]
    assert client.all_users == [] and client.participants == []


def test_ignore_weekday_reaches_both_sends(tmp_path, monkeypatch):
    client = FakeClient()
    run(tmp_path, monkeypatch, client, argv=["--ignore-weekday"])
    run(tmp_path, monkeypatch, client, argv=["--ignore-weekday", "--study_key", "influweb"])
    assert client.all_users[0][1] is True and client.participants[0][3] is True


def test_a_malformed_whatsapp_section_is_a_clear_error(tmp_path, monkeypatch):
    client = FakeClient()
    with pytest.raises(WhatsAppTemplateError, match="whatsapp.template"):
        run(tmp_path, monkeypatch, client, SETTINGS + 'whatsapp:\n  template: ""\n', BOTH)
    assert client.all_users == []


def test_dry_run_shows_template_params_and_recipients(tmp_path, monkeypatch, capsys):
    client = FakeClient()
    settings = SETTINGS.replace('"newsletter"', '"study-reminder"') + whatsapp(button_0="loginToken")
    run(tmp_path, monkeypatch, client, settings, BOTH, ["--dry-run", "--study_key", "influweb"])
    out = capsys.readouterr().out
    assert "season_start_v2" in out and "button_0" in out and "influweb" in out and "nothing sent" in out


def test_dry_run_still_stops_on_a_template_not_approved(tmp_path, monkeypatch):
    client = FakeClient()
    with pytest.raises(WhatsAppTemplateError, match="Nothing saved or sent"):
        run(tmp_path, monkeypatch, client, SETTINGS + WHATSAPP, {"it": "APPROVED"}, ["--dry-run"])


def test_the_condition_of_the_settings_reaches_the_study_send(tmp_path, monkeypatch):
    client = FakeClient()
    settings = SETTINGS + 'condition:\n  dtype: "num"\n  num: 0\n'
    run(tmp_path, monkeypatch, client, settings, argv=["--study_key", "influweb"])
    assert client.participants[0][1] == {"dtype": "num", "num": 0}


def test_a_whatsapp_value_that_is_not_a_section_is_a_clear_error(tmp_path, monkeypatch):
    client = FakeClient()
    with pytest.raises(WhatsAppTemplateError, match="must be"):
        run(tmp_path, monkeypatch, client, SETTINGS + 'whatsapp: true\n', BOTH)
    assert client.all_users == []
