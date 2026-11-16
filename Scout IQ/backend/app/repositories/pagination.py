"""Count and page SQLAlchemy queries in PostgreSQL before materializing rows."""
from math import ceil


def paginate(query, page: int, page_size: int):
    total = query.order_by(None).count()
    return {
        "players": query.offset((page - 1) * page_size).limit(page_size).all(),
        "total": total, "page": page, "page_size": page_size,
        "total_pages": ceil(total / page_size),
        "has_next": page * page_size < total, "has_previous": page > 1,
    }
