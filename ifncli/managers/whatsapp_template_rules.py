"""
    Local validation of a WhatsApp template definition against Meta's component rules, run before
    registering it. Pure: no I/O, no network.

    `validate_template` never sends anything to Meta; it only catches, ahead of time, the mistakes
    Meta's own review would reject the template for. All comparisons of types/formats/categories are
    case-insensitive, since Meta's own docs mix "MARKETING"/"marketing" and "OTP"/"otp".
"""
import re
from typing import Any, Dict, List, Optional, Tuple

NAME_RE = re.compile(r"^[a-z0-9_]+$")
NAMED_PARAM_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
VARIABLE_RE = re.compile(r"\{\{([^{}]*)\}\}")
PACKAGE_SEGMENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
SIGNATURE_HASH_RE = re.compile(r"^[A-Za-z0-9+/=]{11}$")

CATEGORIES = {"MARKETING", "UTILITY", "AUTHENTICATION"}
PARAMETER_FORMATS = {"NAMED", "POSITIONAL"}
COMPONENT_TYPES = {"HEADER", "BODY", "FOOTER", "BUTTONS", "CAROUSEL", "LIMITED_TIME_OFFER"}
HEADER_FORMATS = {"TEXT", "IMAGE", "VIDEO", "GIF", "DOCUMENT", "LOCATION"}
MEDIA_HEADER_FORMATS = {"IMAGE", "VIDEO", "GIF", "DOCUMENT"}
CARD_HEADER_FORMATS = {"IMAGE", "VIDEO", "PRODUCT"}
CARD_COMPONENT_TYPES = {"HEADER", "BODY", "BUTTONS"}
CARD_BUTTON_TYPES = {"QUICK_REPLY", "URL", "PHONE_NUMBER", "SPM"}
BUTTON_TYPES = {"CATALOG", "COPY_CODE", "FLOW", "MPM", "OTP", "PHONE_NUMBER", "QUICK_REPLY", "URL", "VOICE_CALL", "SPM"}
OTP_TYPES = {"COPY_CODE", "ONE_TAP", "ZERO_TAP"}
FLOW_ACTIONS = {"NAVIGATE", "DATA_EXCHANGE"}


def validate_template(template: Any) -> List[str]:
    """Return the list of problems with a template definition; empty when it is valid."""
    if not isinstance(template, dict):
        return ["the template must be a JSON object"]

    errors: List[str] = []
    errors.extend(_validate_name(template.get("name")))
    errors.extend(_validate_language(template.get("language")))

    category = _normalize(template.get("category"))
    if category not in CATEGORIES:
        errors.append("category must be one of MARKETING, UTILITY, AUTHENTICATION (got %r)" % template.get("category"))

    parameter_format, format_errors = _validate_parameter_format(template.get("parameter_format"))
    errors.extend(format_errors)

    components = template.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        return errors

    by_type: Dict[str, Dict] = {}
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            errors.append("component %d must be a JSON object" % index)
            continue
        ctype = _normalize(component.get("type"))
        if ctype not in COMPONENT_TYPES:
            errors.append("component %d has an unknown type %r" % (index, component.get("type")))
            continue
        if ctype in by_type:
            errors.append("only one %s component is allowed" % ctype)
            continue
        by_type[ctype] = component

    if "BODY" not in by_type:
        errors.append("a BODY component is required")

    has_lto = "LIMITED_TIME_OFFER" in by_type
    observed_formats = set()

    if "HEADER" in by_type:
        header_errors, header_format = _validate_header(by_type["HEADER"], category, parameter_format)
        errors.extend(header_errors)
        if header_format:
            observed_formats.add(header_format)
    if "BODY" in by_type:
        body_errors, body_format = _validate_body(by_type["BODY"], category, parameter_format, limit=600 if has_lto else 1024)
        errors.extend(body_errors)
        if body_format:
            observed_formats.add(body_format)
    if "FOOTER" in by_type:
        errors.extend(_validate_footer(by_type["FOOTER"], category, has_lto))
    if "BUTTONS" in by_type:
        errors.extend(_validate_buttons(by_type["BUTTONS"], category))
    if "CAROUSEL" in by_type:
        carousel_errors, carousel_formats = _validate_carousel(by_type["CAROUSEL"], category, parameter_format)
        errors.extend(carousel_errors)
        observed_formats |= carousel_formats
    if "LIMITED_TIME_OFFER" in by_type:
        errors.extend(_validate_limited_time_offer(by_type["LIMITED_TIME_OFFER"], category))

    if len(observed_formats) > 1:
        errors.append("the template mixes NAMED and POSITIONAL parameters across components")

    if category == "AUTHENTICATION":
        if "HEADER" in by_type:
            errors.append("AUTHENTICATION templates cannot have a HEADER component")
        if "BUTTONS" in by_type:
            for index, button in enumerate(by_type["BUTTONS"].get("buttons") or []):
                if isinstance(button, dict) and _normalize(button.get("type")) != "OTP":
                    errors.append("BUTTONS: AUTHENTICATION templates can only have OTP buttons (button %d)" % index)

    if "CAROUSEL" in by_type and category != "MARKETING":
        errors.append("CAROUSEL is only allowed in MARKETING templates")
    if has_lto and category != "MARKETING":
        errors.append("LIMITED_TIME_OFFER is only allowed in MARKETING templates")

    return errors


# --- top-level fields -----------------------------------------------------

def _normalize(value) -> Optional[str]:
    return value.upper() if isinstance(value, str) else None


def _validate_name(name) -> List[str]:
    if not isinstance(name, str) or name == "" or len(name) > 512 or not NAME_RE.match(name):
        return ["name must match ^[a-z0-9_]+$ and be at most 512 characters (got %r)" % name]
    return []


def _validate_language(language) -> List[str]:
    if not isinstance(language, str) or language == "":
        return ["language must be a non-empty string"]
    return []


def _validate_parameter_format(value) -> Tuple[Optional[str], List[str]]:
    if value is None:
        return None, []
    normalized = _normalize(value)
    if normalized not in PARAMETER_FORMATS:
        return None, ["parameter_format must be NAMED or POSITIONAL (got %r)" % value]
    return normalized, []


# --- variables in text -----------------------------------------------------

def _text_variables(text: str) -> Tuple[Optional[str], List, List[str]]:
    """
        Scan `text` for Meta placeholders. Returns (format, tokens, errors): format is
        "POSITIONAL" (tokens = list of ints, in order of appearance) or "NAMED" (tokens = list of
        names, in order of appearance), or None when there are no placeholders.
    """
    tokens = VARIABLE_RE.findall(text)
    if not tokens:
        return None, [], []
    numeric = [t for t in tokens if t.isdigit()]
    named = [t for t in tokens if not t.isdigit()]
    if numeric and named:
        return None, [], ["mixes positional ({{n}}) and named ({{name}}) variables in the same text"]
    if numeric:
        return "POSITIONAL", [int(t) for t in tokens], []
    errors = ["variable name '%s' must match ^[a-z_][a-z0-9_]*$" % t for t in named if not NAMED_PARAM_RE.match(t)]
    return "NAMED", tokens, errors


def _check_positional_contiguous(tokens: List[int], context: str) -> List[str]:
    distinct = sorted(set(tokens))
    if distinct != list(range(1, len(distinct) + 1)):
        return ["%s: positional variables must be contiguous starting at 1 (got %s)" % (context, distinct)]
    return []


# --- HEADER -----------------------------------------------------------------

def _validate_header(component: Dict, category: Optional[str], parameter_format: Optional[str]) -> Tuple[List[str], Optional[str]]:
    errors: List[str] = []
    fmt = _normalize(component.get("format"))
    if fmt not in HEADER_FORMATS:
        return ["HEADER: format must be one of TEXT, IMAGE, VIDEO, GIF, DOCUMENT, LOCATION (got %r)" % component.get("format")], None

    if fmt == "TEXT":
        return _validate_header_text(component, parameter_format)
    if fmt == "LOCATION":
        if category not in ("UTILITY", "MARKETING"):
            errors.append("HEADER: LOCATION format is only allowed in UTILITY or MARKETING templates")
        return errors, None
    # IMAGE, VIDEO, GIF, DOCUMENT
    example = component.get("example")
    has_handle = isinstance(example, dict) and bool(example.get("header_handle"))
    has_handle_file = isinstance(example, dict) and bool(example.get("header_handle_file"))
    if not has_handle and not has_handle_file:
        errors.append("HEADER: a media header requires example.header_handle or example.header_handle_file")
    return errors, None


def _validate_header_text(component: Dict, parameter_format: Optional[str]) -> Tuple[List[str], Optional[str]]:
    errors: List[str] = []
    text = component.get("text")
    if not isinstance(text, str) or text == "":
        return ["HEADER: TEXT header requires text"], None
    if len(text) > 60:
        errors.append("HEADER: text must be at most 60 characters")

    fmt, tokens, var_errors = _text_variables(text)
    errors.extend("HEADER: %s" % e for e in var_errors)
    if fmt == "POSITIONAL" and len(set(tokens)) > 1:
        errors.append("HEADER: text header supports at most 1 variable")
    if fmt and parameter_format and fmt != parameter_format:
        errors.append("HEADER: variables use %s format but the template declares parameter_format=%s" % (fmt, parameter_format))

    example = component.get("example") or {}
    if fmt == "POSITIONAL":
        errors.extend(_check_positional_contiguous(tokens, "HEADER"))
        header_text = example.get("header_text")
        if not (isinstance(header_text, list) and len(header_text) == 1 and isinstance(header_text[0], str) and header_text[0]):
            errors.append("HEADER: missing or malformed example.header_text")
    elif fmt == "NAMED":
        names = sorted(set(tokens))
        named_params = example.get("header_text_named_params")
        if not _named_params_cover(named_params, names):
            errors.append("HEADER: missing or malformed example.header_text_named_params")
    return errors, fmt


# --- BODY (and card body) ---------------------------------------------------

def _named_params_cover(named_params, names: List[str]) -> bool:
    if not isinstance(named_params, list):
        return False
    given = {}
    for param in named_params:
        if not isinstance(param, dict):
            return False
        given[param.get("param_name")] = param.get("example")
    if sorted(n for n in given.keys() if isinstance(n, str)) != names:
        return False
    return all(isinstance(v, str) and v != "" for v in given.values())


def _body_text_example_ok(body_text: Any, n: int) -> bool:
    # Meta's carousel template docs: "If message body text uses a single variable, body_text value can be a string,
    # otherwise it must be an array containing an array of strings."
    if n == 1 and isinstance(body_text, str) and body_text != "":
        return True
    return (isinstance(body_text, list) and len(body_text) == 1 and isinstance(body_text[0], list)
            and len(body_text[0]) == n and all(isinstance(v, str) and v != "" for v in body_text[0]))


def _validate_body_text(text: Optional[str], category: Optional[str], parameter_format: Optional[str],
                         limit: int, example: Any, context: str) -> Tuple[List[str], Optional[str]]:
    errors: List[str] = []
    if not isinstance(text, str) or text == "":
        return ["%s: text is required" % context], None
    if len(text) > limit:
        errors.append("%s: text must be at most %d characters" % (context, limit))
    fmt, tokens, var_errors = _text_variables(text)
    errors.extend("%s: %s" % (context, e) for e in var_errors)

    if fmt and parameter_format and fmt != parameter_format:
        errors.append("%s: variables use %s format but the template declares parameter_format=%s" % (context, fmt, parameter_format))

    example = example if isinstance(example, dict) else {}
    if fmt == "POSITIONAL":
        errors.extend(_check_positional_contiguous(tokens, context))
        n = len(set(tokens))
        if not _body_text_example_ok(example.get("body_text"), n):
            errors.append("%s: missing or malformed example.body_text for %d variable(s)" % (context, n))
    elif fmt == "NAMED":
        names = sorted(set(tokens))
        if not _named_params_cover(example.get("body_text_named_params"), names):
            errors.append("%s: missing or malformed example.body_text_named_params" % context)
    return errors, fmt


def _validate_implicit_authentication_body_example(example: Any, context: str) -> List[str]:
    """
        AUTHENTICATION's fixed preset body ("{{1}} is your verification code.") is not written in
        the template JSON at all, so no `text` and no example is required. When an example is
        still given (as the project's own approved templates do), it must be well-formed for the
        implicit single positional variable.
    """
    if example is None:
        return []
    example = example if isinstance(example, dict) else {}
    if not _body_text_example_ok(example.get("body_text"), 1):
        return ["%s: malformed example.body_text (expected one example for the implicit {{1}})" % context]
    return []


def _validate_body(component: Dict, category: Optional[str], parameter_format: Optional[str], limit: int) -> Tuple[List[str], Optional[str]]:
    text = component.get("text")
    if category == "AUTHENTICATION" and text is None:
        errors = list(_validate_implicit_authentication_body_example(component.get("example"), "BODY"))
        add_security_recommendation = component.get("add_security_recommendation")
        if add_security_recommendation is not None and not isinstance(add_security_recommendation, bool):
            errors.append("BODY: add_security_recommendation must be a boolean")
        return errors, "POSITIONAL"
    return _validate_body_text(text, category, parameter_format, limit, component.get("example"), "BODY")


# --- FOOTER ------------------------------------------------------------------

def _validate_footer(component: Dict, category: Optional[str], has_lto: bool) -> List[str]:
    errors: List[str] = []
    if has_lto:
        errors.append("FOOTER: not allowed together with LIMITED_TIME_OFFER")

    if category == "AUTHENTICATION":
        if component.get("text") is not None:
            errors.append("FOOTER: AUTHENTICATION templates use code_expiration_minutes, not text")
        code_expiration = component.get("code_expiration_minutes")
        if code_expiration is not None:
            if isinstance(code_expiration, bool) or not isinstance(code_expiration, int) or not (1 <= code_expiration <= 90):
                errors.append("FOOTER: code_expiration_minutes must be an integer between 1 and 90")
        return errors

    text = component.get("text")
    if not isinstance(text, str) or text == "":
        errors.append("FOOTER: text is required")
        return errors
    if len(text) > 60:
        errors.append("FOOTER: text must be at most 60 characters")
    if VARIABLE_RE.search(text):
        errors.append("FOOTER: text cannot contain variables")
    return errors


# --- LIMITED_TIME_OFFER -------------------------------------------------------

def _validate_limited_time_offer(component: Dict, category: Optional[str]) -> List[str]:
    errors: List[str] = []
    if category != "MARKETING":
        errors.append("LIMITED_TIME_OFFER is only allowed in MARKETING templates")
    lto = component.get("limited_time_offer")
    if not isinstance(lto, dict):
        errors.append("LIMITED_TIME_OFFER: a limited_time_offer object is required")
        return errors
    text = lto.get("text")
    if not isinstance(text, str) or text == "" or len(text) > 16:
        errors.append("LIMITED_TIME_OFFER: text is required and at most 16 characters")
    has_expiration = lto.get("has_expiration")
    if has_expiration is not None and not isinstance(has_expiration, bool):
        errors.append("LIMITED_TIME_OFFER: has_expiration must be a boolean")
    return errors


# --- BUTTONS -------------------------------------------------------------------

def _validate_buttons(component: Dict, category: Optional[str]) -> List[str]:
    errors: List[str] = []
    buttons = component.get("buttons")
    if not isinstance(buttons, list) or not buttons:
        return ["BUTTONS: buttons must be a non-empty list"]
    if len(buttons) > 10:
        errors.append("BUTTONS: at most 10 buttons in total")

    types: List[Optional[str]] = []
    counts: Dict[str, int] = {}
    for index, button in enumerate(buttons):
        ctx = "BUTTONS: button %d" % index
        if not isinstance(button, dict):
            errors.append("%s must be a JSON object" % ctx)
            types.append(None)
            continue
        btype = _normalize(button.get("type"))
        if btype not in BUTTON_TYPES:
            errors.append("%s has an unknown type %r" % (ctx, button.get("type")))
            types.append(None)
            continue
        types.append(btype)
        counts[btype] = counts.get(btype, 0) + 1
        if btype == "OTP":
            errors.extend(_validate_otp_button(button, category, ctx))
        else:
            errors.extend(_validate_button_fields(button, btype, ctx))

    if counts.get("URL", 0) > 2:
        errors.append("BUTTONS: at most 2 URL buttons")
    if counts.get("PHONE_NUMBER", 0) > 1:
        errors.append("BUTTONS: at most 1 PHONE_NUMBER button")
    if counts.get("COPY_CODE", 0) > 1:
        errors.append("BUTTONS: at most 1 COPY_CODE button")
    if counts.get("OTP", 0) > 1:
        errors.append("BUTTONS: at most 1 OTP button")

    # [templates_components]: buttons must form at most two contiguous blocks - one of
    # QUICK_REPLY buttons and one of every other type - in either order. "URL, Quick Reply, URL"
    # is invalid even with a single quick reply button, because it splits the URL block in two.
    runs = 0
    previous_is_quick_reply = None
    for btype in types:
        is_quick_reply = btype == "QUICK_REPLY"
        if is_quick_reply != previous_is_quick_reply:
            runs += 1
        previous_is_quick_reply = is_quick_reply
    if runs > 2:
        errors.append("BUTTONS: QUICK_REPLY buttons must be grouped together with other buttons forming at most two blocks")

    return errors


def _validate_button_fields(button: Dict, btype: str, ctx: str) -> List[str]:
    errors: List[str] = []
    if btype in ("URL", "PHONE_NUMBER", "QUICK_REPLY", "VOICE_CALL"):
        text = button.get("text")
        max_len = 20 if btype == "VOICE_CALL" else 25
        if not isinstance(text, str) or text == "":
            errors.append("%s: text is required" % ctx)
        elif len(text) > max_len:
            errors.append("%s: text must be at most %d characters" % (ctx, max_len))

    if btype == "URL":
        url = button.get("url")
        if not isinstance(url, str) or url == "" or len(url) > 2000:
            errors.append("%s: url is required and at most 2000 characters" % ctx)
        else:
            fmt, tokens, var_errors = _text_variables(url)
            errors.extend("%s: %s" % (ctx, e) for e in var_errors)
            if fmt == "POSITIONAL" and len(set(tokens)) > 1:
                errors.append("%s: url supports at most 1 variable" % ctx)
            # Meta's components docs: "Supports 1 variable, appended to the end of the URL string."
            if fmt is not None and not url.endswith("}}"):
                errors.append("%s: url variable must be appended to the end of the url" % ctx)
            if fmt is not None:
                example = button.get("example")
                if not (isinstance(example, list) and len(example) == 1 and isinstance(example[0], str) and example[0]):
                    errors.append("%s: url with a variable requires example" % ctx)
    elif btype == "PHONE_NUMBER":
        phone = button.get("phone_number")
        if not isinstance(phone, str) or phone == "" or len(phone) > 20:
            errors.append("%s: phone_number is required and at most 20 characters" % ctx)
    elif btype == "VOICE_CALL":
        ttl = button.get("ttl_minutes")
        if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, int) or not (1440 <= ttl <= 43200)):
            errors.append("%s: ttl_minutes must be an integer between 1440 and 43200" % ctx)
    elif btype == "COPY_CODE":
        example = button.get("example")
        if not isinstance(example, str) or example == "" or len(example) > 20:
            errors.append("%s: example is required and at most 20 characters" % ctx)
    elif btype == "FLOW":
        has_id = bool(button.get("flow_id"))
        has_name = bool(button.get("flow_name"))
        has_json = bool(button.get("flow_json"))
        if sum([has_id, has_name, has_json]) != 1:
            errors.append("%s: FLOW requires exactly one of flow_id, flow_name, flow_json" % ctx)
        action = button.get("flow_action")
        if action is not None:
            normalized_action = _normalize(action)
            if normalized_action not in FLOW_ACTIONS:
                errors.append("%s: flow_action must be navigate or data_exchange" % ctx)
            elif normalized_action == "NAVIGATE" and not button.get("navigate_screen"):
                errors.append("%s: navigate_screen is required when flow_action is navigate" % ctx)
    # CATALOG, MPM, SPM: Meta documents no creation-time fields beyond the type and the text;
    # accepted as a bare button type.
    return errors


def _validate_otp_button(button: Dict, category: Optional[str], ctx: str) -> List[str]:
    errors: List[str] = []
    if category != "AUTHENTICATION":
        errors.append("%s: OTP buttons are only allowed in AUTHENTICATION templates" % ctx)

    for field in ("text", "autofill_text"):
        value = button.get(field)
        if value is not None and (not isinstance(value, str) or len(value) > 25):
            errors.append("%s: %s must be at most 25 characters" % (ctx, field))

    otp_type = _normalize(button.get("otp_type"))
    if otp_type not in OTP_TYPES:
        errors.append("%s: otp_type must be COPY_CODE, ONE_TAP or ZERO_TAP (got %r)" % (ctx, button.get("otp_type")))
        return errors

    if otp_type in ("ONE_TAP", "ZERO_TAP"):
        errors.extend(_validate_supported_apps(button.get("supported_apps"), ctx))
        if otp_type == "ZERO_TAP" and button.get("zero_tap_terms_accepted") is not True:
            errors.append("%s: zero_tap_terms_accepted must be true for ZERO_TAP" % ctx)
    return errors


def _validate_supported_apps(apps, ctx: str) -> List[str]:
    if not isinstance(apps, list) or not apps:
        return ["%s: supported_apps is required with at least one app" % ctx]
    errors: List[str] = []
    for index, app in enumerate(apps):
        app_ctx = "%s: supported_apps[%d]" % (ctx, index)
        if not isinstance(app, dict):
            errors.append("%s must be a JSON object" % app_ctx)
            continue
        package_name = app.get("package_name")
        if not _is_valid_package_name(package_name):
            errors.append("%s: package_name must have at least two dot-separated segments, each starting with "
                           "a letter and using only [A-Za-z0-9_], at most 224 characters" % app_ctx)
        signature_hash = app.get("signature_hash")
        if not isinstance(signature_hash, str) or not SIGNATURE_HASH_RE.match(signature_hash):
            errors.append("%s: signature_hash must be exactly 11 characters of [A-Za-z0-9+/=]" % app_ctx)
    return errors


def _is_valid_package_name(package_name) -> bool:
    if not isinstance(package_name, str) or package_name == "" or len(package_name) > 224:
        return False
    segments = package_name.split(".")
    return len(segments) >= 2 and all(PACKAGE_SEGMENT_RE.match(segment) for segment in segments)


# --- CAROUSEL -------------------------------------------------------------------

def _validate_carousel(component: Dict, category: Optional[str], parameter_format: Optional[str]):
    errors: List[str] = []
    cards = component.get("cards")
    if not isinstance(cards, list) or not (2 <= len(cards) <= 10):
        return ["CAROUSEL: cards must be a list with 2 to 10 items"], set()

    key_sets = []
    has_body_flags = []
    observed_formats = set()
    for card_index, card in enumerate(cards):
        ctx = "CAROUSEL: card %d" % card_index
        if not isinstance(card, dict):
            errors.append("%s must be a JSON object" % ctx)
            continue
        card_components = card.get("components")
        if not isinstance(card_components, list) or not card_components:
            errors.append("%s: components must be a non-empty list" % ctx)
            continue

        by_type: Dict[str, Dict] = {}
        for component_index, card_component in enumerate(card_components):
            if not isinstance(card_component, dict):
                errors.append("%s: component %d must be a JSON object" % (ctx, component_index))
                continue
            ctype = _normalize(card_component.get("type"))
            if ctype not in CARD_COMPONENT_TYPES:
                errors.append("%s: components may only be HEADER, BODY or BUTTONS (got %r)" % (ctx, card_component.get("type")))
                continue
            if ctype in by_type:
                errors.append("%s: only one %s component is allowed" % (ctx, ctype))
                continue
            by_type[ctype] = card_component

        if "HEADER" not in by_type:
            errors.append("%s: a HEADER component is required" % ctx)
        else:
            errors.extend(_validate_card_header(by_type["HEADER"], ctx))
        if "BODY" in by_type:
            body_errors, body_format = _validate_body_text(by_type["BODY"].get("text"), category, parameter_format,
                                                             160, by_type["BODY"].get("example"), ctx)
            errors.extend(body_errors)
            if body_format:
                observed_formats.add(body_format)
        if "BUTTONS" in by_type:
            errors.extend(_validate_card_buttons(by_type["BUTTONS"], ctx))

        key_sets.append(frozenset(by_type.keys()))
        has_body_flags.append("BODY" in by_type)

    if key_sets and len(set(key_sets)) > 1:
        errors.append("CAROUSEL: all cards must have the same components")
    if has_body_flags and len(set(has_body_flags)) > 1:
        errors.append("CAROUSEL: either all cards or none must have a BODY component")

    return errors, observed_formats


def _validate_card_header(component: Dict, ctx: str) -> List[str]:
    fmt = _normalize(component.get("format"))
    if fmt not in CARD_HEADER_FORMATS:
        return ["%s: HEADER format must be IMAGE, VIDEO or PRODUCT (got %r)" % (ctx, component.get("format"))]
    if fmt == "PRODUCT":
        return []
    example = component.get("example")
    has_handle = isinstance(example, dict) and bool(example.get("header_handle"))
    has_handle_file = isinstance(example, dict) and bool(example.get("header_handle_file"))
    if not has_handle and not has_handle_file:
        return ["%s: media HEADER requires example.header_handle or example.header_handle_file" % ctx]
    return []


def _validate_card_buttons(component: Dict, ctx: str) -> List[str]:
    buttons = component.get("buttons")
    if not isinstance(buttons, list) or not buttons:
        return ["%s: BUTTONS requires a non-empty buttons list" % ctx]
    errors: List[str] = []
    if len(buttons) > 2:
        errors.append("%s: at most 2 buttons per card" % ctx)
    for index, button in enumerate(buttons):
        button_ctx = "%s: button %d" % (ctx, index)
        if not isinstance(button, dict):
            errors.append("%s must be a JSON object" % button_ctx)
            continue
        btype = _normalize(button.get("type"))
        if btype not in CARD_BUTTON_TYPES:
            errors.append("%s has a type not allowed in a card (%r)" % (button_ctx, button.get("type")))
            continue
        if btype == "SPM":
            continue
        errors.extend(_validate_button_fields(button, btype, button_ctx))
    return errors
