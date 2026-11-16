# ===================== v32.3 钩子 suffix / schema 31 =====================

def apply(c):
    from bot.infra import repo_meta
    try:
        c.execute("ALTER TABLE cron_tasks ADD COLUMN suffix VARCHAR(200) NULL")
    except Exception:
        try:
            c.connection.rollback()
        except Exception:
            pass
    repo_meta.set_value("schema_version", "31", cursor=c)
    try:
        c.connection.commit()
    except Exception:
        pass
    return True
