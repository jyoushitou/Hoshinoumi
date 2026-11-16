# ===================== v28.2 插件核心表 / schema 30 =====================

PLUGIN_TABLES = (
    "plugin_registry",
    "plugin_approvals",
    "plugin_permissions",
    "plugin_errors",
    "plugin_schema_version",
    "plugin_registry_generation",
)


def apply(c):
    """幂等创建插件核心表，并把 schema_version 升到 30。"""
    from bot.infra import schema, repo_meta

    made = schema.ensure_tables(c, names=list(PLUGIN_TABLES))
    # v28.4：旧 v28.2 表补 path 列（幂等）
    try:
        c.execute("ALTER TABLE plugin_registry ADD COLUMN path VARCHAR(255) NOT NULL DEFAULT ''")
    except Exception:
        try:
            c.connection.rollback()
        except Exception:
            pass
    try:
        c.execute(
            "INSERT INTO plugin_registry_generation(id, generation) VALUES(1, 0)")
        c.connection.commit()
    except Exception:
        try:
            c.connection.rollback()
        except Exception:
            pass
    repo_meta.set_value("schema_version", "30", cursor=c)
    try:
        c.connection.commit()
    except Exception:
        pass
    return made
