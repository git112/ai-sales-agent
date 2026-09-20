from __future__ import annotations

from typing import Any

from app.store import by_workspace, get_by_id


class DemoAIProvider:
    """Evidence-bound demo intelligence. Never invents contacts or urgency."""

    def understand_business(self, payload: dict) -> dict:
        services = payload.get("services") or []
        products = payload.get("products") or []
        technologies = payload.get("technologies") or []
        description = payload.get("description") or ""
        docs_text = payload.get("documents_text") or ""
        blob = " ".join(
            [
                payload.get("company_name") or "",
                payload.get("website") or "",
                description,
                " ".join(services),
                " ".join(products),
                " ".join(technologies),
                docs_text,
            ]
        ).lower()
        inferred_services = list(services)
        for term, label in [
            ("sharepoint", "SharePoint implementation"),
            ("migration", "SharePoint migration"),
            ("microsoft 365", "Microsoft 365 consulting"),
            ("365", "Microsoft 365 consulting"),
            ("document", "Enterprise document management"),
            ("integration", "Microsoft 365 integration"),
            ("custom", "SharePoint customization"),
        ]:
            if term in blob and label not in inferred_services:
                inferred_services.append(label)
        inferred_tech = list(technologies)
        for term, label in [("sharepoint", "SharePoint"), ("microsoft 365", "Microsoft 365"), ("power platform", "Power Platform")]:
            if term in blob and label not in inferred_tech:
                inferred_tech.append(label)
        roles = payload.get("target_roles") or []
        if not roles and ("sharepoint" in blob or "365" in blob):
            roles = ["CIO", "IT Director", "SharePoint Admin", "Digital Workplace Lead"]
        signals = payload.get("buying_signals") or []
        if not signals and inferred_services:
            signals = [
                "Posted SharePoint implementation or migration requirements",
                "Hiring SharePoint / Microsoft 365 engineers",
            ]
        return {
            "company_summary": description.strip()
            or f"{payload.get('company_name')} provides {', '.join(inferred_services[:4]) or 'professional services'}.",
            "services": inferred_services,
            "products": products,
            "technologies": inferred_tech,
            "industries": payload.get("target_industries") or ([payload.get("industry")] if payload.get("industry") else []),
            "target_customers": payload.get("target_customers") or [],
            "target_roles": roles,
            "locations": payload.get("target_locations") or ([payload.get("location")] if payload.get("location") else []),
            "keywords": payload.get("keywords") or inferred_services[:6],
            "buying_signals": signals,
        }

    def plan_search(self, query: str) -> dict:
        q = (query or "").lower()
        keywords = []
        if "sharepoint" in q:
            keywords.append("SharePoint")
        if "365" in q or "microsoft" in q:
            keywords.append("Microsoft 365")
        if "implement" in q:
            keywords.append("implementation")
        if "migrat" in q:
            keywords.append("migration")
        location = None
        for loc in ["india", "uae", "usa", "pune", "mumbai", "chennai", "ahmedabad"]:
            if loc in q:
                location = loc.title() if loc != "uae" else "UAE"
                break
        return {"keywords": keywords or [query], "location": location, "raw": query}

    def analyze_opportunity(self, profile: dict, opportunity: dict, signals: list[dict], market: list[dict]) -> dict:
        text = " ".join(
            [
                opportunity.get("title") or "",
                opportunity.get("requirement") or "",
                opportunity.get("need") or "",
                " ".join(opportunity.get("technology") or []),
            ]
        ).lower()
        services = [s.lower() for s in (profile.get("services") or [])]
        techs = [t.lower() for t in (profile.get("technologies") or [])]
        service_match = 55
        technology_match = 50
        if any("sharepoint" in s for s in services) and "sharepoint" in text:
            service_match = 95
        elif any(s.split()[0] in text for s in services if s):
            service_match = 78
        if any("sharepoint" in t for t in techs) and "sharepoint" in text:
            technology_match = 94
        elif any("365" in t for t in techs) and "365" in text:
            technology_match = 80
        intent = 48
        if opportunity.get("signal_type") == "Requirement" or "looking for" in text or "partner" in text:
            intent = 92
        elif "evaluat" in text or "explor" in text:
            intent = 70
        freshness = 40
        published = opportunity.get("published_at") or ""
        if published >= "2026-09-15":
            freshness = 90
        elif published >= "2026-09-08":
            freshness = 68
        company_fit = 70
        loc = (opportunity.get("location") or "").lower()
        if any((l or "").lower() in loc for l in (profile.get("locations") or [])):
            company_fit = 85
        total = round(
            service_match * 0.28
            + intent * 0.24
            + freshness * 0.16
            + technology_match * 0.2
            + company_fit * 0.12
        )
        evidence = []
        for sig in signals:
            for ev in sig.get("evidence") or []:
                evidence.append(ev)
        why_match = "Insufficient evidence."
        if service_match >= 90:
            why_match = (
                "The prospect is actively seeking SharePoint implementation support, "
                "which directly matches your SharePoint consulting service."
            )
        elif service_match >= 75:
            why_match = (
                f"The requirement overlaps your services ({', '.join((profile.get('services') or [])[:2])})."
            )
        why_now = "No strong why-now signal detected."
        hiring = any(s.get("signal_type") == "Hiring" for s in signals) or any(
            m.get("kind") == "hiring" and m.get("detected") for m in market
        )
        if freshness >= 85 and hiring:
            why_now = "The requirement was published recently and the company is also hiring for related technical roles."
        elif freshness >= 85:
            why_now = "The requirement was published recently."
        elif hiring:
            why_now = "A related hiring signal is present. Freshness of the core requirement is moderate."
        return {
            "label": "AI Opportunity Score",
            "total": total,
            "service_match": service_match,
            "intent_score": intent,
            "freshness_score": freshness,
            "technology_match": technology_match,
            "company_fit": company_fit,
            "disclaimer": "Explainable heuristic, not a scientifically precise ranking.",
            "why_match": why_match,
            "why_now": why_now,
            "evidence": evidence,
            "risks": opportunity.get("risks")
            or (["Budget not disclosed."] if not opportunity.get("budget") else []),
            "missing_information": opportunity.get("missing_information")
            or ["Budget", "Decision process"],
            "recommended_action": "Qualify via AI voice campaign, then schedule human follow-up if intent is high.",
        }

    def next_best_action(self, qualification: dict | None, opportunity: dict | None) -> dict:
        interest = (qualification or {}).get("interest_level") or "Unknown"
        if interest in ("Interested", "Demo Requested", "Proposal Requested", "Meeting Requested"):
            return {
                "action": "Schedule a human sales meeting.",
                "why": "Prospect confirmed an active requirement and requested a specialist or proposal.",
                "evidence": (qualification or {}).get("evidence") or [],
                "priority": "HIGH",
            }
        if interest == "Callback":
            return {
                "action": "Call back",
                "why": "Prospect requested a callback.",
                "evidence": (qualification or {}).get("evidence") or [],
                "priority": "HIGH",
            }
        if interest == "Not Interested":
            return {
                "action": "Stop outreach",
                "why": "Prospect declined further contact.",
                "evidence": (qualification or {}).get("evidence") or [],
                "priority": "LOW",
            }
        return {
            "action": "Research company",
            "why": "Qualification is incomplete.",
            "evidence": [],
            "priority": "MEDIUM",
        }

    def copilot(self, question: str, workspace_id: str) -> dict:
        q = question.lower()
        leads = by_workspace("leads", workspace_id)
        opps = by_workspace("opportunities", workspace_id)
        tasks = by_workspace("tasks", workspace_id)
        calls = by_workspace("calls", workspace_id)
        citations = []
        answer = "I can only answer from workspace records. No matching records were found."

        def cite(kind: str, rec: dict):
            citations.append({"type": kind, "id": rec.get("id"), "label": rec.get("company") or rec.get("title") or rec.get("name")})

        if "high-intent" in q or "high intent" in q:
            hits = [l for l in leads if (l.get("intent_level") or "").lower() in ("interested", "high")]
            hits += [l for l in leads if (l.get("opportunity_score") or 0) >= 85]
            seen = set()
            uniq = []
            for h in hits:
                if h["id"] not in seen:
                    seen.add(h["id"])
                    uniq.append(h)
            if uniq:
                answer = "High-priority leads in this workspace: " + ", ".join(f"{x.get('company')} ({x.get('intent_level') or 'score '+str(x.get('opportunity_score'))})" for x in uniq)
                for x in uniq:
                    cite("lead", x)
            else:
                answer = "No high-intent leads are recorded yet. Qualify ABC Technologies via a demo campaign to generate intent."
                abc = get_by_id("leads", "lead_abc")
                if abc:
                    cite("lead", abc)
        elif "callback" in q:
            hits = [l for l in leads if l.get("intent_level") == "Callback"]
            hits += [c for c in calls if c.get("outcome") == "Callback Requested"]
            answer = "Prospects who requested callbacks: " + (", ".join(x.get("company") or x.get("lead_id") for x in hits) if hits else "none recorded.")
            for x in hits:
                cite("record", x)
        elif "contact today" in q or "should i contact" in q or "do next" in q:
            open_tasks = [t for t in tasks if t.get("status") != "complete"]
            top = sorted(opps, key=lambda o: (o.get("score") or {}).get("total") or 0, reverse=True)
            parts = []
            if open_tasks:
                parts.append("Open follow-ups: " + ", ".join(t.get("title") for t in open_tasks[:5]))
                for t in open_tasks[:5]:
                    cite("task", t)
            if top:
                parts.append("Highest AI Opportunity Score: " + top[0].get("title") + " at " + str((top[0].get("score") or {}).get("total")))
                cite("opportunity", top[0])
            answer = " ".join(parts) or "No pending actions in workspace data."
        elif "campaign" in q or "today" in q:
            campaigns = by_workspace("campaigns", workspace_id)
            if campaigns:
                answer = f"{len(campaigns)} campaign(s) on file. Latest status: {campaigns[-1].get('status')}."
                cite("campaign", campaigns[-1])
            else:
                answer = "No campaigns have been launched in this workspace yet."
        elif "why" in q and "priorit" in q:
            abc = get_by_id("opportunities", "opp_abc")
            if abc:
                answer = f"{abc.get('why_match')} {abc.get('why_now')} AI Opportunity Score {abc.get('score', {}).get('total')}/100."
                cite("opportunity", abc)
        else:
            abc = next((o for o in opps if o.get("id") == "opp_abc"), opps[0] if opps else None)
            if abc:
                answer = f"Workspace has {len(opps)} opportunities and {len(leads)} leads. Top record: {abc.get('title')} ({abc.get('source')})."
                cite("opportunity", abc)
        return {"answer": answer, "citations": citations, "grounded": True}


class LiveAIProvider:
    """Stub until an API key is provided. Same task methods as DemoAIProvider."""

    def _blocked(self):
        raise RuntimeError(
            "LIVE AI is not configured. Set AI_PROVIDER and the matching API key, or stay in DEMO MODE."
        )

    def understand_business(self, payload: dict) -> dict:
        self._blocked()

    def plan_search(self, query: str) -> dict:
        self._blocked()

    def analyze_opportunity(self, profile, opportunity, signals, market) -> dict:
        self._blocked()

    def next_best_action(self, qualification, opportunity) -> dict:
        self._blocked()

    def copilot(self, question: str, workspace_id: str) -> dict:
        self._blocked()


demo_ai = DemoAIProvider()
live_ai = LiveAIProvider()
