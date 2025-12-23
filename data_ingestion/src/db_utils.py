from sqlalchemy.dialects.postgresql import insert as pg_insert


async def insert_ignore(session, model, values: dict, index_elements: list[str]):
    stmt = pg_insert(model).values(**values)
    if index_elements:
        stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
    await session.execute(stmt)
    await session.commit()
