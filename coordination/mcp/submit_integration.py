from __future__ import annotations

from typing import Any

from orchestration.conflict_resolver import PRConflictError


class SubmitIntegration:
    def __init__(self, resolver: Any, state_store: Any) -> None:
        self.resolver = resolver
        self.state_store = state_store

    def pre_submit_check(
        self,
        node_id: str,
        pr_id: str,
    ) -> dict:
        pending_prs = getattr(self.state_store, "pending_prs", {})
        try:
            self.resolver.check_open_pr_conflict(node_id, pending_prs)
        except PRConflictError as e:
            return {
                "ok": False,
                "error_code": e.error_code,
                "error_message": str(e),
                "detail": e.detail,
            }
        except Exception as e:
            code = getattr(e, "error_code", "E_INTERNAL_UNEXPECTED")
            return {
                "ok": False,
                "error_code": code,
                "error_message": str(e),
            }
        if hasattr(self.state_store, "set_pending_pr"):
            self.state_store.set_pending_pr(node_id, pr_id)
        return {"ok": True}
