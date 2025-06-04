import base64


def decode_text(base64_string):
    """
    Decodifica um texto codificado em base64

    Args:
        base64_string: String codificada em base64

    Returns:
        Texto decodificado
    """
    base64_bytes = base64_string.encode('utf-8')
    text_bytes = base64.b64decode(base64_bytes)
    return text_bytes.decode('utf-8')
