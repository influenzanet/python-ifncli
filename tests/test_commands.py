import pytest
from cliff.commandmanager import CommandManager

from ifncli.commands import get_commands
from ifncli.shell import MyApp


def command_name(klass):
    return getattr(klass, "name", klass.__name__)


@pytest.mark.parametrize("klass", get_commands(), ids=command_name)
def test_every_command_builds_its_parser(klass):
    # Building the parser also builds the help epilog, which cliff 3.10 makes with pkg_resources:
    # without it installed, every `ifn <command>` fails before doing anything.
    app = MyApp(description="InfluenzaNet CLI", version="test", command_manager=CommandManager("ifncli"), deferred_help=True)
    command = klass(app, None, cmd_name=command_name(klass))
    parser = command.get_parser("ifn " + command_name(klass))
    assert parser.format_help()
