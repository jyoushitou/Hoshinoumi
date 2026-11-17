# ===================== v34 schema 32：学习规划 + 情境 =====================

def apply(c):
    from bot.infra import schema, repo_meta
    names = ["study_plans", "owner_presence"]
    schema.ensure_tables(c, names=names)
    repo_meta.set_value("schema_version", "32", cursor=c)
    try:
        c.connection.commit()
    except Exception:
        pass
    return names
