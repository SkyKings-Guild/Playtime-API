import secrets

def create_key():
    return secrets.token_urlsafe(64)