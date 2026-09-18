import reflex as rx
import csv
import io
import logging
from sqlalchemy import text
from app.security import read_session
from app.states.auth_state import AuthState
from app.states.competency_workspace_state import GAP_CTE


class CompetencyReportState(rx.State):
    error: str = ""

    @rx.event
    async def export_gaps(self):
        self.error = ""
        try:
            auth = await self.get_state(AuthState)
            uid = read_session(auth.session_cookie)
            async with rx.asession() as session:
                actor = (
                    await session.execute(
                        text(
                            "SELECT id FROM cc_user WHERE id=:uid AND role='admin' AND is_active=true AND approval_status='approved'"
                        ),
                        {"uid": uid},
                    )
                ).first()
                if not actor:
                    self.error = "Approved administrator access is required."
                    return
                result = await session.execute(
                    text(f"""{GAP_CTE}
                    SELECT organization,department,role,subject,name AS competency,full_name AS trainee,current_level,required_level,
                    CASE WHEN current_level IS NULL OR required_level IS NULL THEN NULL WHEN required_level>current_level THEN required_level-current_level ELSE 0 END AS gap,
                    last_verified_at FROM basis ORDER BY organization,department,role,name,user_id LIMIT 10001
                """),
                    {"uid": uid, "admin": True},
                )
                headings = list(result.keys())
                rows = result.all()
            if len(rows) > 10000:
                self.error = "More than 10,000 rows match. Export was stopped to avoid silent truncation."
                return
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headings)
            for row in rows:
                cells = []
                for value in row:
                    cell = "" if value is None else str(value)
                    cells.append(
                        f"'{cell}"
                        if cell.lstrip().startswith(
                            ("=", "+", "-", "@", "\t", "\r")
                        )
                        else cell
                    )
                writer.writerow(cells)
            return rx.download(
                data=output.getvalue(),
                filename="capacity-connect-competency-gaps.csv",
            )
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "Unable to export the competency gap report."
