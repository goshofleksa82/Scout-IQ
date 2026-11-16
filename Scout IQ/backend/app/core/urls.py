def normalize_database_url(value):
    for prefix in ('postgres://','postgresql://'):
        if value.startswith(prefix): return 'postgresql+psycopg://'+value[len(prefix):]
    return value
