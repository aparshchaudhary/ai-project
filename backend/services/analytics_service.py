"""
Analytics Service.
Aggregates usage statistics, response latency, and command distributions.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import func

from backend.database.database import SessionLocal
from backend.database.models import CommandHistory
from backend.models.schemas import AnalyticsResponse


class AnalyticsService:
    def get_analytics(self) -> AnalyticsResponse:
        db = SessionLocal()
        try:
            total = db.query(CommandHistory).count()
            success = db.query(CommandHistory).filter(CommandHistory.status == "success").count()
            failed = db.query(CommandHistory).filter(CommandHistory.status == "failed").count()

            # Avg response time
            avg_time = db.query(func.avg(CommandHistory.execution_time_ms)).scalar() or 0.0

            # Commands today
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = db.query(CommandHistory).filter(CommandHistory.created_at >= today_start).count()

            # Most used intents
            intent_counts = (
                db.query(CommandHistory.recognized_intent, func.count(CommandHistory.id).label("count"))
                .group_by(CommandHistory.recognized_intent)
                .order_by(func.count(CommandHistory.id).desc())
                .limit(7)
                .all()
            )
            most_used_intents = [{"intent": r[0], "count": r[1]} for r in intent_counts]

            # Most used apps from open_application entities
            app_records = db.query(CommandHistory.entities_json).filter(
                CommandHistory.recognized_intent == "open_application"
            ).all()

            app_counter: Dict[str, int] = {}
            for rec in app_records:
                try:
                    data = json.loads(rec[0] or "{}")
                    app_name = data.get("application") or data.get("raw_app")
                    if app_name:
                        app_counter[app_name] = app_counter.get(app_name, 0) + 1
                except Exception:
                    continue

            sorted_apps = sorted(app_counter.items(), key=lambda x: x[1], reverse=True)[:5]
            most_used_apps = [{"app": k, "count": v} for k, v in sorted_apps]

            # Timeline past 7 days
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=6)
            timeline_data = []
            for i in range(7):
                day = (seven_days_ago + timedelta(days=i)).date()
                day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
                day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=timezone.utc)
                count = db.query(CommandHistory).filter(
                    CommandHistory.created_at >= day_start,
                    CommandHistory.created_at <= day_end
                ).count()
                timeline_data.append({"date": day.strftime("%b %d"), "count": count})

            success_rate = round((success / total * 100), 1) if total > 0 else 100.0

            return AnalyticsResponse(
                total_commands=total,
                successful_commands=success,
                failed_commands=failed,
                success_rate_percent=success_rate,
                average_response_time_ms=round(avg_time, 2),
                commands_today=today_count,
                most_used_intents=most_used_intents,
                most_used_apps=most_used_apps,
                commands_timeline=timeline_data
            )
        finally:
            db.close()


analytics_service = AnalyticsService()
