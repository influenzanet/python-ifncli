from pathlib import Path

import pytest

from ifncli.platform import PlatformException, PlatformResources, ResourcesLayoutPath


def test_layout_path_is_the_path_it_was_given(tmp_path):
    path = ResourcesLayoutPath(tmp_path)
    assert str(path) == str(tmp_path)
    assert path == tmp_path
    assert path.is_dir()
    assert (path / "platform.yaml") == tmp_path / "platform.yaml"


def test_layout_path_builds_from_several_segments(tmp_path):
    path = ResourcesLayoutPath(str(tmp_path), "resources")
    assert path == tmp_path / "resources"


def test_layout_path_default_locations(tmp_path):
    path = ResourcesLayoutPath(tmp_path)
    assert path.get_study_path("influweb") == tmp_path / "study" / "influweb"
    assert path.get_survey_file("influweb", "weekly") == tmp_path / "study" / "influweb" / "surveys" / "weekly.json"
    assert path.get_study_rules_file("influweb") == tmp_path / "study" / "influweb" / "studyRules.json"
    assert path.get_study_props_file("influweb") == tmp_path / "study" / "influweb" / "props.yaml"
    assert path.get_auto_messages_path("weekly_reminder") == tmp_path / "auto_messages" / "weekly_reminder"
    assert path.get_whatsapp_templates_path() == tmp_path / "whatsapp_templates"
    assert path.get_whatsapp_template_file("it", "season_start_v2") == tmp_path / "whatsapp_templates" / "it" / "season_start_v2.json"


def test_layout_path_custom_locations(tmp_path):
    path = ResourcesLayoutPath(tmp_path, studies_path="studies/output", auto_messages_path="auto", whatsapp_templates_path="wa")
    assert path.get_study_path("influweb") == tmp_path / "studies" / "output" / "influweb"
    assert path.get_auto_messages_path("weekly_reminder") == tmp_path / "auto" / "weekly_reminder"
    assert path.get_whatsapp_template_file("en", "t") == tmp_path / "wa" / "en" / "t.json"


def test_platform_reads_the_layout_and_vars_of_platform_yaml(tmp_path):
    for folder in ("studies/output", "auto", "wa"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "platform.yaml").write_text(
        "studies_path: studies/output\n"
        "auto_messages_path: auto\n"
        "whatsapp_templates_path: wa\n"
        "vars:\n"
        "  default_language: it\n"
        "  domain: example.org\n"
    )
    platform = PlatformResources(tmp_path, {"domain": "staging.example.org"})
    path = platform.get_path()
    assert path == tmp_path
    assert path.get_study_path("influweb") == tmp_path / "studies" / "output" / "influweb"
    assert path.get_auto_messages_path("weekly_reminder") == tmp_path / "auto" / "weekly_reminder"
    assert path.get_whatsapp_template_file("it", "t") == tmp_path / "wa" / "it" / "t.json"
    assert platform.get_vars() == {"default_language": "it", "domain": "staging.example.org"}
    assert platform.get_vars_from() == {"default_language": "platform_file", "domain": "config"}


def test_platform_without_platform_yaml_uses_the_default_layout(tmp_path):
    platform = PlatformResources(str(tmp_path), None)
    assert platform.get_path().get_study_path("influweb") == tmp_path / "study" / "influweb"
    assert platform.get_vars() == {}


def test_platform_refuses_a_path_that_is_not_a_directory(tmp_path):
    with pytest.raises(PlatformException, match="is not a directory"):
        PlatformResources(tmp_path / "missing", None)


def test_platform_refuses_a_layout_folder_that_does_not_exist(tmp_path):
    (tmp_path / "platform.yaml").write_text("studies_path: nowhere\n")
    with pytest.raises(PlatformException, match="Studies path"):
        PlatformResources(tmp_path, None)
