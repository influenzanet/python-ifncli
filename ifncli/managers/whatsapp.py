"""
    Helpers for the WhatsApp commands: template files, Meta approval states and the binding of a
    platform message to an approved template. Everything here is free of I/O so it can be tested
    without Meta or the platform.
"""
import copy
import time
from typing import Dict, List, Optional, Tuple

from .messaging.utils import bind_vars

# Meta retires Graph API versions; a config without `api_version` uses this one.
DEFAULT_API_VERSION = "v26.0"

APPROVED = "APPROVED"


class WhatsAppTemplateError(Exception):
    pass


def bind_template_vars(template, variables: Optional[Dict]):
    """
        Return a copy of a template definition where every {=name=} in a string is replaced by the
        platform variable of that name (e.g. {=domain=} from the `vars` of the context config).
        Meta's own placeholders such as {{1}} are left as they are. An unknown variable is an error:
        a template registered with a literal {=domain=} would be approved and unusable.
    """
    problems = []

    def walk(value):
        if isinstance(value, str):
            bound, found, _ = bind_vars(value, variables or {})
            problems.extend(found)
            return bound
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    bound = walk(template)
    if problems:
        raise WhatsAppTemplateError("Unresolved template variables: %s (define them under `vars` in the config)" % ", ".join(sorted(set(problems))))
    return bound


def missing_approvals(statuses: Dict[str, str], languages: List[str]) -> List[Tuple[str, str]]:
    """
        Return the languages, in the given order, whose template is not APPROVED on Meta, with the
        state Meta reports ("NOT FOUND" when the template does not exist in that language).
    """
    return [(lang, statuses.get(lang, "NOT FOUND")) for lang in languages if statuses.get(lang) != APPROVED]


def next_time_too_close(next_time, now: Optional[int] = None, margin: int = 600) -> bool:
    """
        True when the auto message is due within `margin` seconds, or already due. The scheduler
        rewrites an auto message only when it is due: outside that window a read followed by a save
        cannot overlap with it.
    """
    if now is None:
        now = int(time.time())
    return int(next_time) - now <= margin


def read_binding(settings: Dict) -> Tuple[str, Dict[str, str]]:
    """
        Read the `whatsapp` section of an auto message settings.yaml:

            whatsapp:
              template: weekly_reminder_v2
              params:
                button_0: loginToken

        `params` maps each template parameter to the message content key that fills it.
    """
    if "whatsapp" not in settings:
        raise WhatsAppTemplateError("No `whatsapp` section in the settings: add `whatsapp: {template: <name>, params: {...}}`")
    section = settings.get("whatsapp")
    if not isinstance(section, dict):
        raise WhatsAppTemplateError("The `whatsapp` section must be `{template: <name>, params: {...}}`")
    name = section.get("template")
    if not isinstance(name, str) or name == "":
        raise WhatsAppTemplateError("`whatsapp.template` must be the name of the template registered on Meta")
    params = section.get("params", {}) or {}
    if not isinstance(params, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in params.items()):
        raise WhatsAppTemplateError("`whatsapp.params` must map parameter names to content keys, e.g. `button_0: loginToken`")
    return name, dict(params)


def read_template_binding(bindings, message_type: str) -> Tuple[str, Dict[str, str]]:
    """
        Read the entry of a message type in the whatsapp.yaml of an e-mail template folder, keyed by
        message type like subjects.yaml:

            study-reminder:
              template: study_reminder_v1
              params:
                button_0: loginToken
    """
    if not isinstance(bindings, dict) or message_type not in bindings:
        raise WhatsAppTemplateError("whatsapp.yaml has no entry for '%s': add `%s: {template: <name>, params: {...}}`" % (message_type, message_type))
    entry = bindings[message_type]
    if not isinstance(entry, dict):
        raise WhatsAppTemplateError("'%s' in whatsapp.yaml must be `{template: <name>, params: {...}}`" % message_type)
    return read_binding({"whatsapp": entry})


# Message types for which the messaging service puts a login token (loginToken, loginUrl) in the
# content of each send; for every other type a parameter filled with it is missing at send time.
LOGIN_TOKEN_MESSAGE_TYPES = ("weekly", "study-reminder")
LOGIN_CONTENT_KEYS = ("loginToken", "loginUrl")


def login_params_without_token(message_type: str, params: Dict[str, str]) -> List[str]:
    """
        Return, sorted, the template parameters filled with a login token on a message type that does
        not get one. The platform drops the WhatsApp send of such a message without any error.
    """
    if message_type in LOGIN_TOKEN_MESSAGE_TYPES:
        return []
    return sorted(name for name, key in params.items() if key in LOGIN_CONTENT_KEYS)


def bind(template: Dict, template_name: str, params: Dict[str, str]) -> Dict:
    """
        Return a copy of a message template, as read from the management API, bound to a WhatsApp
        template. An empty name removes the binding: the platform clears it only when the name is
        sent explicitly empty, and parameters without a name are not sent.
    """
    bound = copy.deepcopy(template)
    bound["whatsappTemplateName"] = template_name
    if template_name:
        bound["whatsappParams"] = dict(params)
    else:
        bound.pop("whatsappParams", None)
    return bound


def with_binding(auto_message: Dict, template_name: str, params: Dict[str, str]) -> Dict:
    """Return a copy of an auto message, as read from the management API, whose template is bound (see `bind`)."""
    bound = copy.deepcopy(auto_message)
    bound["template"] = bind(bound.get("template", {}), template_name, params)
    return bound
