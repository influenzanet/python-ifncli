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
auto_message_types = [
    'registration',
    'invitation',
    'verify-email',
    'verification-code',
    'password-reset',
    'password-changed',
    'account-id-changed',  # email address changed
    'account-deleted',
    EMAIL_TYPE_WEEKLY
]

# Custom sendable message types
custom_message_types = [
    EMAIL_TYPE_STUDY_REMINDER,
    EMAIL_TYPE_NEWSLETTER
]

all_message_types = auto_message_types + custom_message_types