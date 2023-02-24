from cliff.command import Command

from . import register
import json
class Login(Command):
    """
    Test login
    """

    name = 'login'

    def take_action(self, parsed_args):
        cfg = self.app.get_configs()
        print("Management API  : %s", cfg["management_api_url"])
        print("Participant API : %s", cfg['participant_api_url'])
        creds = cfg['user_credentials']
        print("Account         : <%s>@%s" % (creds['email'], creds['instanceId']))
        try:
            api = self.app.get_management_api()
            print("Login Ok")
        except Exception as e:
            print("Problem during login")
            print(e)

class ShowConfig(Command):
    """
        show current configuration
    """

    name = 'config:show'

    def get_parser(self, prog_name):
        parser = super(ShowConfig, self).get_parser(prog_name)
        parser.add_argument("--json", help="Output json", action="store_true")
        return parser

    def take_action(self, args):
        cfg = self.app.get_configs()

        cmg = self.app.configManager
        
        platform = self.app.get_platform()

        creds = cfg['user_credentials']
        
        if args.json:
            output = {
                "url": cfg["management_api_url"],
                "email": creds['email'],
                "instance":  creds['instanceId']
            }
            print(json.dumps(output))
            return

        print("Configuration in %s, from context '%s' resolved by %s %s" % (cfg['__config_file'], cmg.get_current(), cmg.cfg_from, cmg.context_file))

        
        print("Management API  : %s" % cfg["management_api_url"])
        print("Participant API : %s" % cfg['participant_api_url'])
        print("Account         : <%s>@%s" % (creds['email'], creds['instanceId']))

        data = platform.get_vars()
        value_from = platform.get_vars_from()
        print("Resolved vars:")
        for name, value in data.items():
            source_name = value_from.get(name, None)
            print(" - %s : %s (%s)" % (name, str(value), source_name))

class ShowContexts(Command):
    name = 'config:contexts'

    def take_action(self, args):
        cfg = self.app.configManager
        print("Known contexts")
        current = cfg.get_current()
        for name, file in cfg.get_contexts().items():
            mark = '*' if current == name else '-'
            print(" %s %s : %s" % (mark, name, file))
        print("Context file : %s" % cfg.context_file)
        print("From : %s" % cfg.cfg_from)

class SwitchContext(Command):
    """
        Switch the current context
    """
    name = 'config:switch'

    def get_parser(self, prog_name):
        parser = super(SwitchContext, self).get_parser(prog_name)
        parser.add_argument("name", help="Name of the context")
        return parser

    def take_action(self, args):
        cfg = self.app.configManager
        cfg.switch(args.name)
        print("Context switched to '%s'" % (cfg.get_current()))

register(Login)
register(ShowConfig)
register(ShowContexts)
register(SwitchContext)