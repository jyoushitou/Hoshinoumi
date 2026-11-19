# ===================== v35 schema 34：Finance =====================

def apply(c):
    from bot.infra import schema, repo_meta
    names = ["finance_entries", "finance_imports"]
    schema.ensure_tables(c, names=names)
    repo_meta.set_value("schema_version", "34", cursor=c)
    try:
        c.connection.commit()
    except Exception:
        pass
    return names
