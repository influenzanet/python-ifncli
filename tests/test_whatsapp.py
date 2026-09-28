import pytest

from ifncli.managers.whatsapp import (
    DEFAULT_API_VERSION,
    WhatsAppTemplateError,
    bind_template_vars,
    missing_approvals,
    next_time_too_close,
    read_binding,
    with_binding,
)


def test_default_api_version_is_a_live_one():
    # v19.0 is retired by Meta: a config without api_version must still work.
    assert DEFAULT_API_VERSION == "v26.0"


def test_bind_template_vars_replaces_variables_in_every_string():
    template = {
        "name": "weekly_reminder_v2",
        "components": [
            {"type": "BUTTONS", "buttons": [{
                "url": "https://{=domain=}/link/study-login?token={{1}}",
                "example": ["https://{=domain=}/link/study-login?token=EXAMPLE"],
            }]},
        ],
    }
    bound = bind_template_vars(template, {"domain": "influenzanet.cloud.orbyta.it"})
    button = bound["components"][0]["buttons"][0]
    assert button["url"] == "https://influenzanet.cloud.orbyta.it/link/study-login?token={{1}}"
    assert button["example"] == ["https://influenzanet.cloud.orbyta.it/link/study-login?token=EXAMPLE"]
    # the original is left untouched
    assert template["components"][0]["buttons"][0]["url"].startswith("https://{=domain=}")


def test_bind_template_vars_refuses_an_unknown_variable():
    with pytest.raises(WhatsAppTemplateError, match="domain"):
        bind_template_vars({"url": "https://{=domain=}/x"}, {})


def test_bind_template_vars_keeps_meta_placeholders():
    assert bind_template_vars({"text": "code {{1}}"}, {}) == {"text": "code {{1}}"}


def test_missing_approvals_lists_every_language_not_approved():
    statuses = {"it": "APPROVED", "en": "PENDING"}
    assert missing_approvals(statuses, ["it", "en", "de"]) == [("en", "PENDING"), ("de", "NOT FOUND")]
    assert missing_approvals(statuses, ["it"]) == []


def test_next_time_too_close():
    now = 1_000_000
    assert next_time_too_close(now + 599, now, 600)
    assert next_time_too_close(now - 10, now, 600)  # already due: the scheduler is about to rewrite it
    assert not next_time_too_close(now + 601, now, 600)
    assert next_time_too_close(str(now + 10), now, 600)  # the API sends int64 as a string


def test_read_binding():
    assert read_binding({"whatsapp": {"template": "weekly_reminder_v2", "params": {"button_0": "loginToken"}}}) == (
        "weekly_reminder_v2", {"button_0": "loginToken"})
    assert read_binding({"whatsapp": {"template": "t"}}) == ("t", {})


@pytest.mark.parametrize("settings", [
    {},
    {"whatsapp": {}},
    {"whatsapp": {"template": ""}},
    {"whatsapp": {"template": "t", "params": ["button_0"]}},
    {"whatsapp": {"template": "t", "params": {"button_0": 3}}},
])
def test_read_binding_refuses_a_missing_or_malformed_section(settings):
    with pytest.raises(WhatsAppTemplateError):
        read_binding(settings)


def test_with_binding_sets_the_binding_on_a_copy():
    stored = {"id": "a1", "nextTime": "1790395200", "template": {"messageType": "weekly", "translations": []}}
    linked = with_binding(stored, "weekly_reminder_v2", {"button_0": "loginToken"})
    assert linked["template"]["whatsappTemplateName"] == "weekly_reminder_v2"
    assert linked["template"]["whatsappParams"] == {"button_0": "loginToken"}
    assert linked["nextTime"] == "1790395200"
    assert "whatsappTemplateName" not in stored["template"]


def test_with_binding_unlink_sends_an_explicit_empty_name_and_no_params():
    stored = {"template": {"messageType": "weekly", "whatsappTemplateName": "old", "whatsappParams": {"button_0": "loginToken"}}}
    unlinked = with_binding(stored, "", {})
    assert unlinked["template"]["whatsappTemplateName"] == ""
    assert "whatsappParams" not in unlinked["template"]
