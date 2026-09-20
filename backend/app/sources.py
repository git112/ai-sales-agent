from __future__ import annotations

from app.store import by_workspace


class SourceAdapter:
    name = "base"
    is_live = False
    is_demo = True

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        raise NotImplementedError


class DemoRequirementAdapter(SourceAdapter):
    name = "Demo Source"
    is_live = False
    is_demo = True

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        keywords = [k.lower() for k in (criteria.get("keywords") or [])]
        location = (criteria.get("location") or "").lower()
        opps = by_workspace("opportunities", workspace_id)
        signals = by_workspace("buying_signals", workspace_id)
        hits = []
        for opp in opps:
            blob = " ".join(
                [
                    opp.get("title") or "",
                    opp.get("requirement") or "",
                    opp.get("need") or "",
                    " ".join(opp.get("technology") or []),
                    opp.get("location") or "",
                ]
            ).lower()
            kw_ok = not keywords or any(k.lower() in blob for k in keywords)
            loc_ok = not location or location in (opp.get("location") or "").lower()
            if kw_ok and loc_ok:
                hits.append({**opp, "adapter": self.name, "is_demo": True})
        if not hits:
            for sig in signals:
                blob = f"{sig.get('title')} {sig.get('description')} {sig.get('location')}".lower()
                if (not keywords or any(k.lower() in blob for k in keywords)) and (
                    not location or location in (sig.get("location") or "").lower()
                ):
                    hits.append({**sig, "adapter": self.name, "is_demo": True, "requirement": sig.get("title")})
        return hits


class PublicWebAdapter(SourceAdapter):
    """Placeholder for permitted public URL fetch. Not used to scrape restricted platforms."""

    name = "Public Web"
    is_live = True
    is_demo = False

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        return []


ADAPTERS = [DemoRequirementAdapter(), PublicWebAdapter()]
