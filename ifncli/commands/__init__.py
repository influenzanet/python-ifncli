COMMANDS = []

# Register a class as a command provider
def register(klass):
    COMMANDS.append(klass)

# Load module to be able to register (autoloader)
from . import config, help, study, email, user, response, survey, stats, participants, survey_repository, help, export

def get_commands():
    return COMMANDS
