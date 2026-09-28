COMMANDS = []

# Register a class as a command provider
def register(klass):
    COMMANDS.append(klass)

# Load module to be able to register (autoloader)
from . import config, study, email, user, response, survey, stats, participants, survey_repository, export, whatsapp, whatsapp_link

def get_commands():
    return COMMANDS
