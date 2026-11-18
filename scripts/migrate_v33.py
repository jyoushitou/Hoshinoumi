# ===================== v35 schema 33：Endpoint + DeliveryHub =====================

def apply(c):
    from bot.infra import schema, repo_meta
    names = ["client_endpoints", "delivery_outbox"]
    schema.ensure_tables(c, names=names)
    repo_meta.set_value("schema_version", "33", cursor=c)
    try:
        c.connection.commit()
    except Exception:
        pass
    return names
