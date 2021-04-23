from cliff.command import Command

from . import register

class Login(Command):
    __name__ = 'login'

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

register(Login)