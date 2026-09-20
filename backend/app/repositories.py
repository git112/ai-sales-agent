from __future__ import annotations

from app.store import by_workspace, create_record, delete_record, get_all, get_by_id, update_record


class JsonRepository:
    def __init__(self, collection: str):
        self.collection = collection

    def all(self) -> list[dict]:
        return get_all(self.collection)

    def by_workspace(self, workspace_id: str) -> list[dict]:
        return by_workspace(self.collection, workspace_id)

    def get(self, record_id: str) -> dict | None:
        return get_by_id(self.collection, record_id)

    def create(self, record: dict) -> dict:
        return create_record(self.collection, record)

    def update(self, record_id: str, patch: dict) -> dict | None:
        return update_record(self.collection, record_id, patch)

    def delete(self, record_id: str) -> bool:
        return delete_record(self.collection, record_id)


class SqliteRepository(JsonRepository):
    """Same interface; persistence is chosen by the store facade (SQLite or JSON fallback)."""


class UserRepository(SqliteRepository):
    def __init__(self):
        super().__init__("users")


class WorkspaceRepository(SqliteRepository):
    def __init__(self):
        super().__init__("workspaces")


class LeadRepository(SqliteRepository):
    def __init__(self):
        super().__init__("leads")


class OpportunityRepository(SqliteRepository):
    def __init__(self):
        super().__init__("opportunities")


class CampaignRepository(SqliteRepository):
    def __init__(self):
        super().__init__("campaigns")


class CallRepository(SqliteRepository):
    def __init__(self):
        super().__init__("calls")


class TaskRepository(SqliteRepository):
    def __init__(self):
        super().__init__("tasks")


class SegmentRepository(SqliteRepository):
    def __init__(self):
        super().__init__("lead_segments")


class SavedSearchRepository(SqliteRepository):
    def __init__(self):
        super().__init__("saved_searches")


class NotificationRepository(SqliteRepository):
    def __init__(self):
        super().__init__("notifications")


class MarketSignalRepository(SqliteRepository):
    def __init__(self):
        super().__init__("market_signals")


class AuditLogRepository(SqliteRepository):
    def __init__(self):
        super().__init__("audit_logs")


class BuyingSignalRepository(SqliteRepository):
    def __init__(self):
        super().__init__("buying_signals")


JsonLeadRepository = LeadRepository
JsonOpportunityRepository = OpportunityRepository
JsonCampaignRepository = CampaignRepository
JsonCallRepository = CallRepository
JsonSegmentRepository = SegmentRepository
JsonSavedSearchRepository = SavedSearchRepository
JsonNotificationRepository = NotificationRepository
SqliteLeadRepository = LeadRepository
SqliteOpportunityRepository = OpportunityRepository
SqliteCampaignRepository = CampaignRepository
SqliteCallRepository = CallRepository
SqliteSegmentRepository = SegmentRepository
SqliteSavedSearchRepository = SavedSearchRepository
SqliteNotificationRepository = NotificationRepository

leads_repo = LeadRepository()
opportunities_repo = OpportunityRepository()
campaigns_repo = CampaignRepository()
calls_repo = CallRepository()
segments_repo = SegmentRepository()
saved_searches_repo = SavedSearchRepository()
notifications_repo = NotificationRepository()
users_repo = UserRepository()
workspaces_repo = WorkspaceRepository()
tasks_repo = TaskRepository()
market_signals_repo = MarketSignalRepository()
audit_logs_repo = AuditLogRepository()
buying_signals_repo = BuyingSignalRepository()
