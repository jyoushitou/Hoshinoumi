# ===================== v35 schema 35：Finance event link =====================

def apply(c):
    from bot.infra import schema, repo_meta
    names = ["finance_entry_meta"]
    schema.ensure_tables(c, names=names)
    repo_meta.set_value("schema_version", "35", cursor=c)
    try:
        c.connection.commit()
    except Exception:
        pass
    return names
