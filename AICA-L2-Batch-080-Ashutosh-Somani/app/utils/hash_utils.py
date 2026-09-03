import hashlib

def calculate_sha256(filepath, chunk_size=8192):
    """
    Calculates SHA-256 for a file using streaming/chunked reading.
    Returns the hex digest.
    """
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()
