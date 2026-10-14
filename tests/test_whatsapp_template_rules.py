import pytest

from ifncli.managers.whatsapp_template_rules import validate_template


def utility_body(text="Hello", **overrides):
    comp = {"type": "BODY", "text": text}
    comp.update(overrides)
    return comp


def base_template(**overrides):
    template = {
        "name": "weekly_reminder_v2",
        "language": "en",
        "category": "UTILITY",
        "components": [utility_body()],
    }
    template.update(overrides)
    return template


def test_a_minimal_valid_template_has_no_errors():
    assert validate_template(base_template()) == []


def test_template_must_be_a_json_object():
    assert validate_template(["not", "a", "dict"]) == ["the template must be a JSON object"]


# --- name --------------------------------------------------------------------

@pytest.mark.parametrize("name", ["Weekly_Reminder", "weekly-reminder", "", "a" * 513, None, 42])
def test_name_must_match_the_grammar(name):
    errors = validate_template(base_template(name=name))
    assert any("name" in e for e in errors)


def test_name_is_case_insensitive_only_in_category_not_in_itself():
    assert validate_template(base_template(name="weekly_reminder_v2")) == []


# --- category ------------------------------------------------------------------

@pytest.mark.parametrize("category", ["marketing", "MARKETING", "Utility", "authentication"])
def test_category_is_case_insensitive(category):
    template = base_template(category=category)
    if category.upper() == "AUTHENTICATION":
        template["components"] = [{"type": "BODY", "example": {"body_text": [["123456"]]}},
                                   {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}]
    assert validate_template(template) == []


@pytest.mark.parametrize("category", ["FREE_SERVICE", "promotional", "", None])
def test_category_must_be_one_of_the_three_known_values(category):
    errors = validate_template(base_template(category=category))
    assert any("category" in e for e in errors)


# --- components ---------------------------------------------------------------

def test_components_must_be_a_non_empty_list():
    assert validate_template(base_template(components=[]))
    assert validate_template(base_template(components="not a list"))


def test_body_is_required():
    errors = validate_template(base_template(components=[{"type": "FOOTER", "text": "bye"}]))
    assert any("BODY component is required" in e for e in errors)


def test_unknown_component_type_is_an_error():
    errors = validate_template(base_template(components=[utility_body(), {"type": "WEIRD"}]))
    assert any("unknown type" in e for e in errors)


def test_duplicate_component_type_is_an_error():
    errors = validate_template(base_template(components=[utility_body(), utility_body()]))
    assert any("only one BODY component" in e for e in errors)


# --- HEADER --------------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["TEXT", "IMAGE", "VIDEO", "GIF", "DOCUMENT", "LOCATION"])
def test_header_accepts_every_known_format(fmt):
    header = {"type": "HEADER", "format": fmt}
    if fmt == "TEXT":
        header["text"] = "Hello"
    elif fmt != "LOCATION":
        header["example"] = {"header_handle": ["4::aW..."]}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert errors == []


def test_header_rejects_an_unknown_format():
    header = {"type": "HEADER", "format": "AUDIO"}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert any("HEADER: format" in e for e in errors)


def test_header_text_over_60_characters_is_rejected():
    header = {"type": "HEADER", "format": "TEXT", "text": "x" * 61}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert any("at most 60 characters" in e for e in errors)


def test_header_text_with_more_than_one_variable_is_rejected():
    header = {"type": "HEADER", "format": "TEXT", "text": "{{1}} and {{2}}", "example": {"header_text": ["a", "b"]}}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert any("at most 1 variable" in e for e in errors)


def test_header_text_variable_requires_a_matching_example():
    header = {"type": "HEADER", "format": "TEXT", "text": "Hi {{1}}"}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert any("example.header_text" in e for e in errors)


def test_header_media_without_a_handle_is_rejected():
    header = {"type": "HEADER", "format": "IMAGE"}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert any("header_handle" in e for e in errors)


def test_header_media_accepts_the_local_header_handle_file_extension():
    header = {"type": "HEADER", "format": "IMAGE", "example": {"header_handle_file": "media/banner.png"}}
    errors = validate_template(base_template(components=[header, utility_body()]))
    assert errors == []


def test_header_location_is_rejected_in_authentication():
    template = {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "example": {"body_text": [["123456"]]}},
                        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}],
    }
    # AUTHENTICATION cannot have a header at all - this exercises that umbrella rule too.
    template["components"].insert(0, {"type": "HEADER", "format": "LOCATION"})
    errors = validate_template(template)
    assert any("AUTHENTICATION templates cannot have a HEADER" in e for e in errors)


# --- BODY: length, variables, examples -----------------------------------------

def test_body_text_is_required():
    errors = validate_template(base_template(components=[{"type": "BODY"}]))
    assert any("BODY: text is required" in e for e in errors)


def test_body_over_1024_characters_is_rejected():
    errors = validate_template(base_template(components=[utility_body(text="x" * 1025)]))
    assert any("at most 1024 characters" in e for e in errors)


def test_body_over_600_characters_is_rejected_with_a_limited_time_offer():
    components = [
        utility_body(text="x" * 601),
        {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::a"]}},
        {"type": "LIMITED_TIME_OFFER", "limited_time_offer": {"text": "Sale!", "has_expiration": True}},
    ]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("at most 600 characters" in e for e in errors)


def test_body_positional_variables_must_be_contiguous_from_one():
    body = utility_body(text="Hi {{1}} your code is {{3}}", example={"body_text": [["Pablo", "123"]]})
    errors = validate_template(base_template(components=[body]))
    assert any("contiguous starting at 1" in e for e in errors)


def test_body_positional_example_count_must_match_variable_count():
    body = utility_body(text="Hi {{1}} and {{2}}", example={"body_text": [["Pablo"]]})
    errors = validate_template(base_template(components=[body]))
    assert any("malformed example.body_text" in e for e in errors)


def test_body_positional_single_variable_example_may_be_a_bare_string():
    body = utility_body(text="Hi {{1}}, welcome", example={"body_text": "Pablo"})
    assert validate_template(base_template(components=[body])) == []


def test_body_named_variables_must_match_the_grammar():
    body = utility_body(text="Hi {{First-Name}}", example={"body_text_named_params": [{"param_name": "First-Name", "example": "Pablo"}]})
    errors = validate_template(base_template(components=[body]))
    assert any("variable name" in e for e in errors)


def test_body_named_example_must_cover_every_name_with_a_non_empty_value():
    body = utility_body(text="Hi {{first_name}}, order {{order_number}}",
                         example={"body_text_named_params": [{"param_name": "first_name", "example": "Pablo"}]})
    errors = validate_template(base_template(components=[body]))
    assert any("body_text_named_params" in e for e in errors)


def test_body_named_example_is_accepted_when_complete():
    body = utility_body(text="Hi {{first_name}}, order {{order_number}} is ready", example={"body_text_named_params": [
        {"param_name": "first_name", "example": "Pablo"},
        {"param_name": "order_number", "example": "860198"},
    ]})
    assert validate_template(base_template(components=[body])) == []


def test_body_cannot_mix_positional_and_named_in_the_same_text():
    body = utility_body(text="Hi {{1}} {{first_name}}")
    errors = validate_template(base_template(components=[body]))
    assert any("mixes positional" in e for e in errors)


def test_parameter_format_mismatch_is_rejected():
    body = utility_body(text="Hi {{first_name}}", example={"body_text_named_params": [{"param_name": "first_name", "example": "Pablo"}]})
    errors = validate_template(base_template(components=[body], parameter_format="POSITIONAL"))
    assert any("declares parameter_format=POSITIONAL" in e for e in errors)


def test_unknown_parameter_format_is_rejected():
    errors = validate_template(base_template(parameter_format="RANDOM"))
    assert any("parameter_format" in e for e in errors)


def test_header_and_body_parameter_formats_cannot_be_mixed_across_components():
    # A template is NAMED or POSITIONAL: a positional header with a named body is rejected.
    components = [
        {"type": "HEADER", "format": "TEXT", "text": "Hi {{1}}", "example": {"header_text": ["Pablo"]}},
        utility_body(text="Order {{order_number}}", example={"body_text_named_params": [{"param_name": "order_number", "example": "1"}]}),
    ]
    errors = validate_template(base_template(components=components))
    assert any("mixes NAMED and POSITIONAL" in e for e in errors)


# --- AUTHENTICATION body (the fixed Meta preset) --------------------------------

def test_authentication_body_without_text_or_example_is_accepted():
    template = {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "add_security_recommendation": True},
                        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}],
    }
    assert validate_template(template) == []


def test_authentication_body_add_security_recommendation_must_be_a_boolean():
    template = {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "add_security_recommendation": "yes"},
                        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}],
    }
    errors = validate_template(template)
    assert any("add_security_recommendation" in e for e in errors)


def test_authentication_body_with_an_explicit_example_must_still_be_well_formed():
    template = {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "example": {"body_text": [["123456", "extra"]]}},
                        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}],
    }
    errors = validate_template(template)
    assert any("malformed example.body_text" in e for e in errors)


# --- FOOTER ----------------------------------------------------------------------

def test_footer_text_is_required_outside_authentication():
    errors = validate_template(base_template(components=[utility_body(), {"type": "FOOTER"}]))
    assert any("FOOTER: text is required" in e for e in errors)


def test_footer_over_60_characters_is_rejected():
    errors = validate_template(base_template(components=[utility_body(), {"type": "FOOTER", "text": "x" * 61}]))
    assert any("FOOTER: text must be at most 60 characters" in e for e in errors)


def test_footer_cannot_contain_variables():
    errors = validate_template(base_template(components=[utility_body(), {"type": "FOOTER", "text": "Hi {{1}}"}]))
    assert any("FOOTER: text cannot contain variables" in e for e in errors)


def test_authentication_footer_uses_code_expiration_minutes_not_text():
    template = {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "example": {"body_text": [["123456"]]}},
                        {"type": "FOOTER", "text": "some text"},
                        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}],
    }
    errors = validate_template(template)
    assert any("code_expiration_minutes, not text" in e for e in errors)


def test_authentication_footer_code_expiration_minutes_range():
    template = {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "example": {"body_text": [["123456"]]}},
                        {"type": "FOOTER", "code_expiration_minutes": 91},
                        {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}],
    }
    errors = validate_template(template)
    assert any("between 1 and 90" in e for e in errors)


def test_footer_forbidden_with_limited_time_offer():
    components = [
        utility_body(),
        {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::a"]}},
        {"type": "FOOTER", "text": "bye"},
        {"type": "LIMITED_TIME_OFFER", "limited_time_offer": {"text": "Sale!"}},
    ]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("not allowed together with LIMITED_TIME_OFFER" in e for e in errors)


# --- BUTTONS: caps and grouping ---------------------------------------------------

def test_buttons_must_be_a_non_empty_list():
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": []}]))
    assert any("buttons must be a non-empty list" in e for e in errors)


def test_at_most_ten_buttons_in_total():
    buttons = [{"type": "QUICK_REPLY", "text": "x%d" % i} for i in range(11)]
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": buttons}]))
    assert any("at most 10 buttons" in e for e in errors)


def test_at_most_two_url_buttons():
    buttons = [{"type": "URL", "text": "a", "url": "https://x/a"}, {"type": "URL", "text": "b", "url": "https://x/b"},
               {"type": "URL", "text": "c", "url": "https://x/c"}]
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": buttons}]))
    assert any("at most 2 URL buttons" in e for e in errors)


def test_at_most_one_phone_number_button():
    buttons = [{"type": "PHONE_NUMBER", "text": "Call", "phone_number": "1"}, {"type": "PHONE_NUMBER", "text": "Call2", "phone_number": "2"}]
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": buttons}]))
    assert any("at most 1 PHONE_NUMBER" in e for e in errors)


def test_at_most_one_copy_code_button():
    buttons = [{"type": "COPY_CODE", "example": "A"}, {"type": "COPY_CODE", "example": "B"}]
    errors = validate_template(base_template(category="MARKETING", components=[utility_body(), {"type": "BUTTONS", "buttons": buttons}]))
    assert any("at most 1 COPY_CODE" in e for e in errors)


@pytest.mark.parametrize("buttons", [
    [{"type": "QUICK_REPLY", "text": "a"}, {"type": "URL", "text": "b", "url": "https://x"}, {"type": "QUICK_REPLY", "text": "c"}],
    [{"type": "URL", "text": "a", "url": "https://x"}, {"type": "QUICK_REPLY", "text": "b"}, {"type": "URL", "text": "c", "url": "https://y"}],
])
def test_quick_reply_buttons_must_be_grouped_together(buttons):
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": buttons}]))
    assert any("grouped together" in e for e in errors)


@pytest.mark.parametrize("buttons", [
    [{"type": "QUICK_REPLY", "text": "a"}, {"type": "QUICK_REPLY", "text": "b"}],
    [{"type": "QUICK_REPLY", "text": "a"}, {"type": "QUICK_REPLY", "text": "b"}, {"type": "URL", "text": "c", "url": "https://x"},
     {"type": "PHONE_NUMBER", "text": "d", "phone_number": "1"}],
    [{"type": "URL", "text": "a", "url": "https://x"}, {"type": "PHONE_NUMBER", "text": "b", "phone_number": "1"},
     {"type": "QUICK_REPLY", "text": "c"}, {"type": "QUICK_REPLY", "text": "d"}],
])
def test_valid_quick_reply_groupings_are_accepted(buttons):
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": buttons}]))
    assert errors == []


def test_unknown_button_type_is_rejected():
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [{"type": "WEIRD"}]}]))
    assert any("unknown type" in e for e in errors)


# --- URL buttons: variable and example ---------------------------------------------

def test_url_button_requires_url():
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [{"type": "URL", "text": "Shop"}]}]))
    assert any("url is required" in e for e in errors)


def test_url_button_with_a_variable_requires_an_example():
    button = {"type": "URL", "text": "Shop", "url": "https://x/shop?promo={{1}}"}
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert any("url with a variable requires example" in e for e in errors)


def test_url_button_variable_must_be_at_the_end():
    button = {"type": "URL", "text": "Shop", "url": "https://x/{{1}}/shop", "example": ["promo"]}
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert any("appended to the end" in e for e in errors)


def test_url_button_with_a_trailing_variable_and_example_is_accepted():
    button = {"type": "URL", "text": "Shop", "url": "https://x/shop?promo={{1}}", "example": ["summer2023"]}
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert errors == []


def test_url_button_supports_at_most_one_variable():
    button = {"type": "URL", "text": "Shop", "url": "https://x/{{1}}/{{2}}", "example": ["a"]}
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert any("at most 1 variable" in e for e in errors)


# --- OTP buttons: one-tap, zero-tap, AUTHENTICATION restrictions ----------------------

def auth_template(button):
    return {
        "name": "auth_tpl", "language": "en", "category": "AUTHENTICATION",
        "components": [{"type": "BODY", "example": {"body_text": [["123456"]]}}, {"type": "BUTTONS", "buttons": [button]}],
    }


def test_otp_button_only_allowed_in_authentication():
    errors = validate_template(base_template(components=[utility_body(), {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]}]))
    assert any("only allowed in AUTHENTICATION" in e for e in errors)


def test_otp_type_must_be_known():
    errors = validate_template(auth_template({"type": "OTP", "otp_type": "WEIRD"}))
    assert any("otp_type must be" in e for e in errors)


def test_one_tap_requires_supported_apps():
    errors = validate_template(auth_template({"type": "OTP", "otp_type": "ONE_TAP"}))
    assert any("supported_apps is required" in e for e in errors)


def test_one_tap_supported_apps_fields_are_validated():
    button = {"type": "OTP", "otp_type": "ONE_TAP", "supported_apps": [{"package_name": "com", "signature_hash": "short"}]}
    errors = validate_template(auth_template(button))
    assert any("package_name" in e for e in errors) and any("signature_hash" in e for e in errors)


def test_one_tap_with_valid_supported_apps_is_accepted():
    button = {"type": "OTP", "otp_type": "ONE_TAP",
              "supported_apps": [{"package_name": "com.example.luckyshrub", "signature_hash": "K8a/AINcGX7"}]}
    assert validate_template(auth_template(button)) == []


def test_zero_tap_requires_terms_accepted():
    button = {"type": "OTP", "otp_type": "ZERO_TAP",
              "supported_apps": [{"package_name": "com.example.luckyshrub", "signature_hash": "K8a/AINcGX7"}]}
    errors = validate_template(auth_template(button))
    assert any("zero_tap_terms_accepted" in e for e in errors)


def test_zero_tap_with_terms_accepted_is_valid():
    button = {"type": "OTP", "otp_type": "ZERO_TAP", "zero_tap_terms_accepted": True,
              "supported_apps": [{"package_name": "com.example.luckyshrub", "signature_hash": "K8a/AINcGX7"}]}
    assert validate_template(auth_template(button)) == []


def test_copy_code_otp_needs_no_supported_apps():
    assert validate_template(auth_template({"type": "OTP", "otp_type": "COPY_CODE"})) == []


def test_authentication_buttons_can_only_be_otp():
    template = auth_template({"type": "OTP", "otp_type": "COPY_CODE"})
    template["components"][1]["buttons"].append({"type": "QUICK_REPLY", "text": "x"})
    errors = validate_template(template)
    assert any("can only have OTP buttons" in e for e in errors)


# --- VOICE_CALL and FLOW buttons ------------------------------------------------------

def test_voice_call_button_text_and_ttl_limits():
    button = {"type": "VOICE_CALL", "text": "x" * 21, "ttl_minutes": 100}
    errors = validate_template(base_template(category="MARKETING", components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert any("at most 20 characters" in e for e in errors)
    assert any("between 1440 and 43200" in e for e in errors)


def test_voice_call_button_within_limits_is_accepted():
    button = {"type": "VOICE_CALL", "text": "Call Now", "ttl_minutes": 1440}
    errors = validate_template(base_template(category="MARKETING", components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert errors == []


def test_flow_button_requires_exactly_one_identifier():
    button = {"type": "FLOW", "text": "Go", "flow_id": "1", "flow_name": "x"}
    errors = validate_template(base_template(category="MARKETING", components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert any("exactly one of flow_id" in e for e in errors)


def test_flow_navigate_action_requires_a_screen():
    button = {"type": "FLOW", "text": "Go", "flow_id": "1", "flow_action": "navigate"}
    errors = validate_template(base_template(category="MARKETING", components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert any("navigate_screen is required" in e for e in errors)


def test_flow_navigate_with_screen_is_accepted():
    button = {"type": "FLOW", "text": "Go", "flow_id": "1", "flow_action": "navigate", "navigate_screen": "WELCOME"}
    errors = validate_template(base_template(category="MARKETING", components=[utility_body(), {"type": "BUTTONS", "buttons": [button]}]))
    assert errors == []


# --- LIMITED_TIME_OFFER ---------------------------------------------------------------

def test_limited_time_offer_only_allowed_in_marketing():
    components = [utility_body(), {"type": "LIMITED_TIME_OFFER", "limited_time_offer": {"text": "Sale!"}}]
    errors = validate_template(base_template(category="UTILITY", components=components))
    assert any("only allowed in MARKETING" in e for e in errors)


def test_limited_time_offer_text_length_limit():
    components = [utility_body(), {"type": "LIMITED_TIME_OFFER", "limited_time_offer": {"text": "x" * 17}}]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("at most 16 characters" in e for e in errors)


def test_limited_time_offer_has_expiration_must_be_boolean():
    components = [utility_body(), {"type": "LIMITED_TIME_OFFER", "limited_time_offer": {"text": "Sale!", "has_expiration": "yes"}}]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("has_expiration must be a boolean" in e for e in errors)


def test_a_complete_limited_time_offer_template_is_accepted():
    components = [
        {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::aW..."]}},
        {"type": "LIMITED_TIME_OFFER", "limited_time_offer": {"text": "Expiring offer!", "has_expiration": True}},
        utility_body(text="Good news, {{1}}! Use code {{2}} today!", example={"body_text": [["Pablo", "CARIBE25"]]}),
        {"type": "BUTTONS", "buttons": [
            {"type": "COPY_CODE", "example": "CARIBE25"},
            {"type": "URL", "text": "Book now!", "url": "https://x/offers?code={{1}}", "example": ["https://x/offers?ref=n3mtql"]},
        ]},
    ]
    assert validate_template(base_template(category="MARKETING", components=components)) == []


# --- CAROUSEL ------------------------------------------------------------------------

def media_card(button_text="Shop"):
    return {"components": [
        {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": ["4::an..."]}},
        {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": "More"}, {"type": "URL", "text": button_text, "url": "https://x/shop"}]},
    ]}


def test_carousel_only_allowed_in_marketing():
    components = [utility_body(), {"type": "CAROUSEL", "cards": [media_card(), media_card()]}]
    errors = validate_template(base_template(category="UTILITY", components=components))
    assert any("CAROUSEL is only allowed in MARKETING" in e for e in errors)


def test_carousel_needs_between_two_and_ten_cards():
    components = [utility_body(), {"type": "CAROUSEL", "cards": [media_card()]}]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("2 to 10 items" in e for e in errors)


def test_carousel_cards_must_have_the_same_components():
    card_with_body = media_card()
    card_with_body["components"].insert(1, {"type": "BODY", "text": "Hi"})
    components = [utility_body(), {"type": "CAROUSEL", "cards": [media_card(), card_with_body]}]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("same components" in e for e in errors) or any("BODY component" in e for e in errors)


def test_carousel_card_header_requires_image_video_or_product():
    card = {"components": [{"type": "HEADER", "format": "TEXT", "text": "x"}, media_card()["components"][1]]}
    components = [utility_body(), {"type": "CAROUSEL", "cards": [card, media_card()]}]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("HEADER format must be IMAGE, VIDEO or PRODUCT" in e for e in errors)


def test_carousel_card_allows_at_most_two_buttons():
    card = media_card()
    card["components"][1]["buttons"].append({"type": "PHONE_NUMBER", "text": "Call", "phone_number": "1"})
    components = [utility_body(), {"type": "CAROUSEL", "cards": [card, media_card()]}]
    errors = validate_template(base_template(category="MARKETING", components=components))
    assert any("at most 2 buttons per card" in e for e in errors)


def test_carousel_product_card_header_is_accepted():
    card = {"components": [{"type": "HEADER", "format": "PRODUCT"}, {"type": "BUTTONS", "buttons": [{"type": "SPM", "text": "View"}]}]}
    components = [utility_body(), {"type": "CAROUSEL", "cards": [card, card]}]
    assert validate_template(base_template(category="MARKETING", components=components)) == []


def test_a_complete_media_carousel_is_accepted():
    components = [
        utility_body(text="Rare succulents! {{1}}, have a look", example={"body_text": [["Pablo"]]}),
        {"type": "CAROUSEL", "cards": [media_card("Shop1"), media_card("Shop2")]},
    ]
    assert validate_template(base_template(category="MARKETING", components=components)) == []


# Meta refuses a BODY whose text starts or ends with a variable (error 2388299, "Parametri iniziali
# o finali non consentiti"), also when only punctuation follows the last variable: seen when
# registering on the test number "... fino al {{2}}." and "... entro il {{scadenza}}.".
@pytest.mark.parametrize("text", [
    "{{1}} is ready",
    "  {{1}} is ready",
    "Ready until {{1}}",
    "Ready until {{1}}.",
    "Ready until {{1}} !",
    "Ready until {{1}}…",
])
def test_body_starting_or_ending_with_a_variable_is_rejected(text):
    body = utility_body(text=text, example={"body_text": [["x"]]})
    errors = validate_template(base_template(components=[body]))
    assert any("must not start or end with a variable" in e for e in errors), errors


def test_named_body_ending_with_a_variable_is_rejected():
    body = utility_body(text="Paid by {{due}}.", example={"body_text_named_params": [{"param_name": "due", "example": "x"}]})
    errors = validate_template(base_template(parameter_format="NAMED", components=[body]))
    assert any("must not start or end with a variable" in e for e in errors), errors


def test_body_with_variables_inside_the_text_is_accepted():
    body = utility_body(text="Ready until {{1}}, see you on the site.", example={"body_text": [["x"]]})
    assert validate_template(base_template(components=[body])) == []


def test_card_body_ending_with_a_variable_is_rejected():
    from ifncli.managers.whatsapp_template_rules import _validate_body_text
    errors, _ = _validate_body_text("Card {{1}}", "MARKETING", None, 160, {"body_text": [["x"]]}, "CAROUSEL card 0 BODY")
    assert any("must not start or end with a variable" in e for e in errors), errors
