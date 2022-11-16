"""
Messaging service common infos
"""

EMAIL_TYPE_REGISTRATION           = "registration"
EMAIL_TYPE_INVITATION             = "invitation"
EMAIL_TYPE_VERIFY_EMAIL           = "verify-email"
EMAIL_TYPE_AUTH_VERIFICATION_CODE = "verification-code"
EMAIL_TYPE_PASSWORD_RESET         = "password-reset"
EMAIL_TYPE_PASSWORD_CHANGED       = "password-changed"
EMAIL_TYPE_ACCOUNT_ID_CHANGED     = "account-id-changed"
EMAIL_TYPE_WEEKLY                 = "weekly"
EMAIL_TYPE_STUDY_REMINDER         = "study-reminder"
EMAIL_TYPE_NEWSLETTER             = "newsletter"
EMAIL_TYPE_ACCOUNT_DELETED        = "account-deleted"

# Messages accepting a template
SYSTEM_MESSAGE_TYPES = [
    'registration',
    'invitation',
    'verify-email',
    'verification-code',
    'password-reset',
    'password-changed',
    'account-id-changed',  # email address changed
    'account-deleted',
]

# Auto messages
BULK_MESSAGE_TYPES = [
    EMAIL_TYPE_WEEKLY,
    EMAIL_TYPE_STUDY_REMINDER,
    EMAIL_TYPE_NEWSLETTER
]

# All useable types for email templates
ALL_MESSAGE_TYPES = BULK_MESSAGE_TYPES + SYSTEM_MESSAGE_TYPES

AUTO_MESSAGE_ALL_USERS =  "all-users"
AUTO_MESSAGE_SCHEDULED_PARTICIPANTS = "scheduled-participant-messages"
AUTO_MESSAGE_RESEARCHER = "researcher-notifications"
AUTO_MESSAGE_STUDY_PARTICIPANTS = "study-participants"

# Bulk and AutoMessage types
AUTO_MESSAGE_TYPES = [
    AUTO_MESSAGE_ALL_USERS,
    AUTO_MESSAGE_SCHEDULED_PARTICIPANTS,
    AUTO_MESSAGE_RESEARCHER,
    AUTO_MESSAGE_STUDY_PARTICIPANTS
]