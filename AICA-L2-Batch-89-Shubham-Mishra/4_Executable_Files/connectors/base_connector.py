"""
Adapter interface for practice-management data connectors. One connector is
built in this timeline (TallyConnector) but the interface exists so adding
Zoho Books / SAP later is a matter of implementing this contract, not
redesigning the backend. See CLAUDE.md Section 2A.
"""
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    @abstractmethod
    def authenticate(self, credentials: dict) -> None: ...

    @abstractmethod
    def fetch_clients(self) -> list[dict]: ...

    @abstractmethod
    def fetch_ledgers(self, client_id: str) -> list[dict]: ...

    @abstractmethod
    def fetch_vouchers(self, client_id: str, date_range: tuple) -> list[dict]: ...

    @abstractmethod
    def fetch_invoices(self, client_id: str) -> list[dict]: ...
