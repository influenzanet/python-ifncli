"""
    Upload of header media samples (`header_handle_file`) so a WhatsApp template can be registered
    with a real `header_handle`, through Meta's Resumable Upload API
    (https://developers.facebook.com/docs/graph-api/guides/upload).

    Planning (finding the files to upload, resolving and checking them) is pure and has no I/O
    beyond `os.path.realpath`, so it can run during --dry-run with no network and no filesystem
    writes. The upload itself takes an injected HTTP poster so tests never call the real Meta API.

    SECURITY: the access token must never appear in a printed message or in an exception's text.
    `requests` embeds the request URL - which carries `access_token` in step 1 - in its own
    exceptions; those are caught here and translated into a message built only from the HTTP
    status and Meta's own error code/message, never from `str(exception)` or the URL.
"""
import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .whatsapp import DEFAULT_API_VERSION, WhatsAppTemplateError

FACEBOOK_API_BASE = "https://graph.facebook.com"

# IMAGE -> JPEG/PNG; VIDEO and GIF -> MP4 (WhatsApp GIFs are MP4 files); DOCUMENT -> PDF: the
# file types the Resumable Upload API accepts.
FORMAT_MIME_TYPES: Dict[str, Dict[str, str]] = {
    "IMAGE": {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"},
    "VIDEO": {".mp4": "video/mp4"},
    "GIF": {".mp4": "video/mp4"},
    "DOCUMENT": {".pdf": "application/pdf"},
}


# --- planning (pure) ---------------------------------------------------------

def find_header_handle_files(template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
        Scan a template's HEADER components, including those inside CAROUSEL cards, for the local
        `example.header_handle_file` extension. Returns one entry per match:
        {"path": <tuple of keys/indices from the template root to the HEADER component>,
         "format": <uppercased HEADER format>, "file": <raw path string from the JSON>}.
        Pure: does not touch the filesystem.
    """
    findings: List[Dict[str, Any]] = []
    components = template.get("components")
    if not isinstance(components, list):
        return findings

    for component_index, component in enumerate(components):
        if not isinstance(component, dict):
            continue
        ctype = component.get("type")
        ctype = ctype.upper() if isinstance(ctype, str) else None
        if ctype == "HEADER":
            entry = _header_handle_file_entry(component, ("components", component_index))
            if entry:
                findings.append(entry)
        elif ctype == "CAROUSEL":
            findings.extend(_find_in_carousel(component, component_index))
    return findings


def _find_in_carousel(carousel: Dict[str, Any], component_index: int) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    cards = carousel.get("cards")
    if not isinstance(cards, list):
        return findings
    for card_index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        card_components = card.get("components")
        if not isinstance(card_components, list):
            continue
        for inner_index, inner in enumerate(card_components):
            if not isinstance(inner, dict):
                continue
            ctype = inner.get("type")
            ctype = ctype.upper() if isinstance(ctype, str) else None
            if ctype == "HEADER":
                path = ("components", component_index, "cards", card_index, "components", inner_index)
                entry = _header_handle_file_entry(inner, path)
                if entry:
                    findings.append(entry)
    return findings


def _header_handle_file_entry(header_component: Dict[str, Any], path: Tuple) -> Optional[Dict[str, Any]]:
    example = header_component.get("example")
    if not isinstance(example, dict):
        return None
    file_value = example.get("header_handle_file")
    if not isinstance(file_value, str) or file_value == "":
        return None
    header_format = header_component.get("format")
    header_format = header_format.upper() if isinstance(header_format, str) else None
    return {"path": path, "format": header_format, "file": file_value}


def resolve_header_handle_file(file_value: str, template_dir, templates_root, header_format: Optional[str]) -> Tuple[Path, str]:
    """
        Resolve `file_value` relative to the template file's own folder, refuse (`realpath`, so
        after symlinks too) anything outside `templates_root`, and check the extension's MIME type
        against `header_format`. Returns (resolved_path, mime_type) or raises WhatsAppTemplateError.
    """
    candidate = Path(template_dir) / file_value
    resolved = Path(os.path.realpath(str(candidate)))
    root = Path(os.path.realpath(str(templates_root)))
    if root != resolved and root not in resolved.parents:
        raise WhatsAppTemplateError("header_handle_file '%s' resolves outside the templates folder" % file_value)

    mime_types = FORMAT_MIME_TYPES.get(header_format or "")
    if mime_types is None:
        raise WhatsAppTemplateError("header_handle_file is not supported for HEADER format %r" % header_format)
    mime = mime_types.get(resolved.suffix.lower())
    if mime is None:
        raise WhatsAppTemplateError("header_handle_file '%s' has an extension not valid for %s header (expected %s)" % (
            file_value, header_format, ", ".join(sorted(set(mime_types.values())))))
    return resolved, mime


def plan_uploads(template: Dict[str, Any], template_file, templates_root) -> List[Dict[str, Any]]:
    """
        Return the list of uploads a template needs: one entry per `header_handle_file` found, each
        resolved and MIME-checked. Raises WhatsAppTemplateError on the first invalid one. Pure:
        no network, only `os.path.realpath` on local paths.
    """
    template_dir = Path(template_file).parent
    plans = []
    for finding in find_header_handle_files(template):
        resolved, mime = resolve_header_handle_file(finding["file"], template_dir, templates_root, finding["format"])
        plans.append({"path": finding["path"], "file": finding["file"], "format": finding["format"],
                       "resolved": resolved, "mime": mime})
    return plans


# --- applying the result of an upload (pure) ---------------------------------

def _get_by_path(root: Dict[str, Any], path: Tuple):
    node = root
    for key in path:
        node = node[key]
    return node


def _set_handle(component: Dict[str, Any], handle: str) -> None:
    example = {key: value for key, value in (component.get("example") or {}).items() if key != "header_handle_file"}
    example["header_handle"] = [handle]
    component["example"] = example


def apply_placeholder_handles(template: Dict[str, Any], plans: List[Dict[str, Any]],
                               placeholder: str = "<WOULD-BE-UPLOADED-HANDLE>") -> Dict[str, Any]:
    """Return a copy of `template` with every planned `header_handle_file` replaced by a placeholder
    handle, for --dry-run previews. No I/O."""
    updated = copy.deepcopy(template)
    for plan in plans:
        _set_handle(_get_by_path(updated, plan["path"]), placeholder)
    return updated


# --- the actual upload --------------------------------------------------------

def _safe_upload_error(step: str, error: requests.exceptions.RequestException) -> str:
    """
        Build an error message from only the HTTP status and Meta's own error code/message. Never
        uses str(error) or the request URL: `requests` embeds the full URL in its exceptions, and
        the step-1 URL carries `access_token` as a query parameter.
    """
    parts = ["media upload failed (%s step)" % step]
    response = getattr(error, "response", None)
    if response is not None:
        parts.append("HTTP %s" % response.status_code)
        try:
            payload = response.json()
        except ValueError:
            payload = None
        meta_error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(meta_error, dict):
            code = meta_error.get("code")
            message = meta_error.get("message")
            if code is not None:
                parts.append("Meta error %s" % code)
            if message:
                parts.append(str(message))
    return ": ".join(parts[:1]) + ((" - " + ", ".join(parts[1:])) if len(parts) > 1 else "")


def upload_header_handle(poster, api_base: str, api_version: str, app_id: str, access_token: str,
                          resolved_path: Path, mime: str) -> str:
    """
        Perform the two Resumable Upload steps for one file and return
        the resulting `header_handle`. `poster` is injected (defaults to `requests` in callers) so
        tests never reach the real Meta API.
    """
    file_bytes = resolved_path.read_bytes()
    start_url = "%s/%s/%s/uploads" % (api_base, api_version, app_id)
    try:
        start_response = poster.post(start_url, params={
            "file_name": resolved_path.name,
            "file_length": len(file_bytes),
            "file_type": mime,
            "access_token": access_token,
        })
        start_response.raise_for_status()
        upload_id = start_response.json().get("id")
    except requests.exceptions.RequestException as error:
        raise WhatsAppTemplateError(_safe_upload_error("start", error)) from None
    except ValueError:
        raise WhatsAppTemplateError("media upload failed (start step): Meta did not return JSON") from None
    if not upload_id:
        raise WhatsAppTemplateError("media upload failed (start step): Meta did not return an upload session id")

    # The second request targets the upload session id returned above ("upload:<id>").
    continue_url = "%s/%s/%s" % (api_base, api_version, upload_id)
    try:
        continue_response = poster.post(continue_url, headers={
            "Authorization": "OAuth %s" % access_token,
            "file_offset": "0",
        }, data=file_bytes)
        continue_response.raise_for_status()
        handle = continue_response.json().get("h")
    except requests.exceptions.RequestException as error:
        raise WhatsAppTemplateError(_safe_upload_error("upload", error)) from None
    except ValueError:
        raise WhatsAppTemplateError("media upload failed (upload step): Meta did not return JSON") from None
    if not handle:
        raise WhatsAppTemplateError("media upload failed (upload step): Meta did not return a header handle")
    return handle


def upload_header_handles(template: Dict[str, Any], template_file, templates_root, wa_config: Dict[str, Any],
                           api_base: str = FACEBOOK_API_BASE, poster=None) -> Dict[str, Any]:
    """
        Return a copy of `template` with every `header_handle_file` uploaded and replaced by the
        real `header_handle` Meta returns. Raises WhatsAppTemplateError when the config is missing
        `app_id`, or on the first upload failure (message never carries the access token).

        `poster` defaults to the `requests` module, resolved here rather than at function
        definition time so a test that monkeypatches this module's `requests` is honoured even
        when it does not pass `poster` explicitly.
    """
    poster = requests if poster is None else poster
    plans = plan_uploads(template, template_file, templates_root)
    if not plans:
        return copy.deepcopy(template)

    app_id = wa_config.get("app_id")
    if not app_id:
        raise WhatsAppTemplateError("WhatsApp config requires 'app_id' to upload header media samples (whatsapp.app_id)")
    access_token = wa_config["access_token"]
    api_version = wa_config.get("api_version", DEFAULT_API_VERSION)

    updated = copy.deepcopy(template)
    for plan in plans:
        handle = upload_header_handle(poster, api_base, api_version, app_id, access_token, plan["resolved"], plan["mime"])
        _set_handle(_get_by_path(updated, plan["path"]), handle)
    return updated
