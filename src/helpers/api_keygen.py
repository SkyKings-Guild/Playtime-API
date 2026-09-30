import secrets

SYSTEM_API_KEY = "G1iouvi2r5IGKZyp2vi9vpKdF5dDNWF1ir6BvhOQaheChhBwgLtwtbolKffpQZY3uqqdb6L-bsoVMR6atwFJXw"

def create_key():
    return secrets.token_urlsafe(64)