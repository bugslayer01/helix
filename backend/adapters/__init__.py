from .base import DomainAdapter  # noqa: F401
from .admissions import AdmissionsAdapter
from .fraud import FraudAdapter
from .hiring import HiringAdapter
from .loans import LoansAdapter
from .moderation import ModerationAdapter

REGISTRY: dict[str, DomainAdapter] = {}


def register_adapter(adapter: DomainAdapter) -> None:
    REGISTRY[adapter.domain_id] = adapter


def get_adapter(domain_id: str) -> DomainAdapter:
    if domain_id not in REGISTRY:
        raise KeyError(f"No adapter registered for domain {domain_id!r}")
    return REGISTRY[domain_id]


def list_domains() -> list[dict[str, str]]:
    return [
        {"id": a.domain_id, "display_name": a.display_name}
        for a in REGISTRY.values()
    ]


for _adapter in (
    LoansAdapter(),
    HiringAdapter(),
    ModerationAdapter(),
    AdmissionsAdapter(),
    FraudAdapter(),
):
    register_adapter(_adapter)
