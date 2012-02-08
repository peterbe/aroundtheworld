def truncate_text(text, characters):
    if len(text) > characters:
        text = text[:characters - 1] + u'\u2026'
    return text
