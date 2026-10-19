from accounts.models import normalize_username


def normalize_name(value):
    """Mesma normalização do `User.username`, para o nome do docente casar com ele."""
    return normalize_username(value)
