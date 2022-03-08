from cliff.command import Command

from . import register

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

    def take_action(self, args):
        cfg = self.app.get_configs()

        print("Configuration file: %s" % cfg['__config_file'])

        platform = self.app.get_platform()

        print("Management API  : %s", cfg["management_api_url"])
        print("Participant API : %s", cfg['participant_api_url'])
        creds = cfg['user_credentials']
        print("Account         : <%s>@%s" % (creds['email'], creds['instanceId']))

        data = platform.get_vars()
        value_from = platform.get_vars_from()
        print("Resolved vars:")
        for name, value in data.items():
            source_name = value_from.get(name, None)
            print(" - %s : %s (%s)" % (name, str(value), source_name))
        

register(Login)
register(ShowConfig)