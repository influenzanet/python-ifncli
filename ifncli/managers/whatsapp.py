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
    section = settings.get("whatsapp")
    if not isinstance(section, dict):
        raise WhatsAppTemplateError("No `whatsapp` section in the settings: add `whatsapp: {template: <name>, params: {...}}`")
    name = section.get("template")
    if not isinstance(name, str) or name == "":
        raise WhatsAppTemplateError("`whatsapp.template` must be the name of the template registered on Meta")
    params = section.get("params", {}) or {}
    if not isinstance(params, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in params.items()):
        raise WhatsAppTemplateError("`whatsapp.params` must map parameter names to content keys, e.g. `button_0: loginToken`")
    return name, dict(params)


def with_binding(auto_message: Dict, template_name: str, params: Dict[str, str]) -> Dict:
    """
        Return a copy of an auto message, as read from the management API, bound to a WhatsApp
        template. An empty name removes the binding: the platform clears it only when the name is
        sent explicitly empty, and parameters without a name are not sent.
    """
    bound = copy.deepcopy(auto_message)
    template = bound.setdefault("template", {})
    template["whatsappTemplateName"] = template_name
    if template_name:
        template["whatsappParams"] = dict(params)
    else:
        template.pop("whatsappParams", None)
    return bound
