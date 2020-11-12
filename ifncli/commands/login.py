from cliff.command import Command

from . import register

class Login(Command):
    __name__ = 'login'

    def take_action(self, parsed_args):
        print("login")

register(Login)