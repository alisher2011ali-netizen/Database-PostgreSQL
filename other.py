import secrets
import string


def generate_other_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))
