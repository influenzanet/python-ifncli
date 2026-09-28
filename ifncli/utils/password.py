import re

# FIXME: this duplicated code should be avoided, implementation taken from see
# user-management-service/pkg/utils/utils.go commit #c27b903
def check_password_strength(password):

    if len(password) < 8:
        return False

    lowercase = re.search(r"[a-z]", password) is not None
    uppercase = re.search(r"[A-Z]", password) is not None
    number = re.search(r"[\d]", password) is not None
    symbol = re.search(r"[\W]", password) is not None

    password_check = sum([lowercase, uppercase, number, symbol]) > 2

    return password_check      