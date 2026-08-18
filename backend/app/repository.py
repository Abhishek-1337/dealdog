from datetime import datetime, timezone
from typing import Protocol

import numpy as np
from sqlalchemy import select

from .models import PricePoint, Product, TrackedProduct
from .types import PriceRecord, ProductRecord, TrackedRecord


class ProductRepo(Protocol):
    def find_nearest(self, embedding: list[float], top_k: int) -> list[tuple[ProductRecord, float]]: ...

    def find_by_identifier(self, values: set[str]) -> ProductRecord | None: ...

    def create_product(self, title: str, attributes: dict, identifiers: list, embedding: list[float]) -> ProductRecord: ...

    def create_tracked(self, product_id: int) -> TrackedRecord: ...

    def add_price_points(self, product_id: int, listings) -> None: ...

    def get_product(self, product_id: int) -> ProductRecord | None: ...

    def get_tracked(self) -> list[tuple[TrackedRecord, ProductRecord]]: ...

    def get_price_history(self, product_id: int) -> list[PriceRecord]: ...


def _product_record(p: Product) -> ProductRecord:
    return ProductRecord(id=p.id, title=p.title, attributes=p.attributes or {}, identifiers=p.identifiers or [])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqlProductRepo:
    def __init__(self, session_factory):
        self._sf = session_factory

    def find_nearest(self, embedding: list[float], top_k: int) -> list[tuple[ProductRecord, float]]:
        with self._sf() as session:
            dist = Product.embedding.cosine_distance(embedding)
            similarity = (1 - dist).label("similarity")
            rows = session.execute(
                select(Product, similarity).order_by(dist).limit(top_k)
            ).all()
            return [(_product_record(p), float(s)) for p, s in rows if p.embedding is not None]

    def find_by_identifier(self, values: set[str]) -> ProductRecord | None:
        with self._sf() as session:
            products = session.execute(select(Product)).scalars().all()
            for p in products:
                if set(p.identifiers or []) & values:
                    return _product_record(p)
            return None

    def create_product(self, title: str, attributes: dict, identifiers: list, embedding: list[float]) -> ProductRecord:
        with self._sf() as session:
            p = Product(title=title, attributes=attributes, identifiers=identifiers, embedding=embedding)
            session.add(p)
            session.commit()
            session.refresh(p)
            return _product_record(p)

    def create_tracked(self, product_id: int) -> TrackedRecord:
        with self._sf() as session:
            t = TrackedProduct(product_id=product_id)
            session.add(t)
            session.commit()
            session.refresh(t)
            return TrackedRecord(id=t.id, product_id=t.product_id)

    def add_price_points(self, product_id: int, listings) -> None:
        with self._sf() as session:
            for listing in listings:
                session.add(
                    PricePoint(
                        product_id=product_id,
                        site=listing.site,
                        price=listing.price,
                        currency=getattr(listing, "currency", "USD"),
                        link=getattr(listing, "link", ""),
                    )
                )
            session.commit()

    def get_product(self, product_id: int) -> ProductRecord | None:
        with self._sf() as session:
            p = session.get(Product, product_id)
            return _product_record(p) if p else None

    def get_tracked(self) -> list[tuple[TrackedRecord, ProductRecord]]:
        with self._sf() as session:
            rows = session.execute(select(TrackedProduct).order_by(TrackedProduct.id)).scalars().all()
            out = []
            for t in rows:
                p = session.get(Product, t.product_id)
                out.append((TrackedRecord(id=t.id, product_id=t.product_id), _product_record(p)))
            return out

    def get_price_history(self, product_id: int) -> list[PriceRecord]:
        with self._sf() as session:
            rows = session.execute(
                select(PricePoint).where(PricePoint.product_id == product_id).order_by(PricePoint.recorded_at)
            ).scalars().all()
            return [
                PriceRecord(
                    site=r.site,
                    price=r.price,
                    currency=r.currency,
                    link=r.link,
                    recorded_at=r.recorded_at.isoformat(),
                )
                for r in rows
            ]


class InMemoryProductRepo:
    def __init__(self):
        self.products: dict[int, ProductRecord] = {}
        self.embeddings: dict[int, list[float]] = {}
        self.tracked: list[TrackedRecord] = []
        self.history: dict[int, list[PriceRecord]] = {}
        self._next_product = 1
        self._next_tracked = 1

    def _cos(self, a: list[float], b: list[float]) -> float:
        av = np.asarray(a, dtype=np.float32)
        bv = np.asarray(b, dtype=np.float32)
        na, nb = float(np.linalg.norm(av)), float(np.linalg.norm(bv))
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(av, bv) / (na * nb))

    def find_nearest(self, embedding: list[float], top_k: int) -> list[tuple[ProductRecord, float]]:
        scored = [(self.products[pid], self._cos(embedding, self.embeddings[pid])) for pid in self.products]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    def find_by_identifier(self, values: set[str]) -> ProductRecord | None:
        for p in self.products.values():
            if set(p.identifiers) & values:
                return p
        return None

    def create_product(self, title: str, attributes: dict, identifiers: list, embedding: list[float]) -> ProductRecord:
        pid = self._next_product
        self._next_product += 1
        p = ProductRecord(id=pid, title=title, attributes=attributes, identifiers=identifiers)
        self.products[pid] = p
        self.embeddings[pid] = embedding
        self.history[pid] = []
        return p

    def create_tracked(self, product_id: int) -> TrackedRecord:
        t = TrackedRecord(id=self._next_tracked, product_id=product_id)
        self._next_tracked += 1
        self.tracked.append(t)
        return t

    def add_price_points(self, product_id: int, listings) -> None:
        for listing in listings:
            self.history[product_id].append(
                PriceRecord(
                    site=listing.site,
                    price=listing.price,
                    currency=getattr(listing, "currency", "USD"),
                    link=getattr(listing, "link", ""),
                    recorded_at=_now(),
                )
            )

    def get_product(self, product_id: int) -> ProductRecord | None:
        return self.products.get(product_id)

    def get_tracked(self) -> list[tuple[TrackedRecord, ProductRecord]]:
        return [(t, self.products[t.product_id]) for t in self.tracked]

    def get_price_history(self, product_id: int) -> list[PriceRecord]:
        return list(self.history.get(product_id, []))
