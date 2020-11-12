COMMANDS = []

# Register a class as a command provider
def register(klass):
    COMMANDS.append(klass)

# Load module to be able to register (autoloader)
from . import login, study, email, user, response

def get_commands():
    return COMMANDS



