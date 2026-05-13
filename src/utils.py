import hashlib

def sha256_content(content: bytes):
    h = hashlib.sha256()
    h.update(content)

    return h.hexdigest()