"""Analytics: participation, completion, certification and assessment outcomes."""

from __future__ import annotations

import reflex as rx
import reflex_xy

from app.components.admin_shell import (
    admin_page,
    cell,
    data_table,
    row_class,
    table_head,
    th,
)
from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
)
from app.states.admin_analytics_state import AdminAnalyticsState


def _participation_chart() -> rx.Component:
    return reflex_xy.chart(
        reflex_xy.bar("course", "enrolled", name="Enrolled", color="#0A1B33"),
        reflex_xy.bar("course", "completed", name="Completed", color="#0D9488"),
        reflex_xy.bar("course", "certified", name="Certified", color="#F59E0B"),
        reflex_xy.x_axis(label="Course index"),
        reflex_xy.y_axis(label="Trainees"),
        reflex_xy.legend(),
        reflex_xy.modebar(False),
        reflex_xy.interaction_config(navigation=False),
        data=AdminAnalyticsState.participation_columns,
        title="Participation, completion and certification by course",
        height="340px",
        class_name="w-full min-w-[300px]",
    )


def _outcome_chart() -> rx.Component:
    return reflex_xy.chart(
        reflex_xy.line(
            "assessment",
            "pass_rate",
            name="Pass rate %",
            color="#0D9488",
            width=2.5,
        ),
        reflex_xy.line(
            "assessment",
            "average_score",
            name="Mean score %",
            color="#0A1B33",
            width=2.5,
        ),
        reflex_xy.x_axis(label="Assessment index"),
        reflex_xy.y_axis(label="Percent"),
        reflex_xy.legend(),
        reflex_xy.modebar(False),
        reflex_xy.interaction_config(navigation=False),
        data=AdminAnalyticsState.outcome_columns,
        title="Assessment pass rate and mean score",
        height="340px",
        class_name="w-full min-w-[300px]",
    )


def _participation_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                f"#{row['index']}",
                class_name="text-[0.7rem] font-semibold text-slate-400",
            )
        ),
        cell(
            rx.el.p(
                row["code"],
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-teal-700",
            ),
            rx.el.p(
                row["title"],
                class_name="max-w-[18rem] text-xs font-medium text-slate-700",
            ),
        ),
        cell(
            rx.el.p(
                row["enrolled"].to_string(),
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                f"{row['active']} active",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['completion']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["completion"]),
                class_name="flex w-28 flex-col gap-1",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['certification']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["certification"], "amber"),
                rx.el.span(
                    f"{row['certified']} certificates",
                    class_name="text-[0.65rem] font-medium text-slate-500",
                ),
                class_name="flex w-28 flex-col gap-1",
            )
        ),
        class_name=row_class(),
    )


def _outcome_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                f"#{row['index']}",
                class_name="text-[0.7rem] font-semibold text-slate-400",
            )
        ),
        cell(
            rx.el.p(
                row["title"],
                class_name="max-w-[18rem] text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["code"],
                class_name="text-[0.65rem] font-medium uppercase tracking-wider text-slate-500",
            ),
        ),
        cell(
            rx.el.p(
                row["attempts"].to_string(),
                class_name="text-xs font-semibold text-slate-700",
            )
        ),
        cell(
            rx.el.p(
                row["results"].to_string(),
                class_name="text-xs font-semibold text-slate-700",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['pass_rate']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["pass_rate"]),
                class_name="flex w-28 flex-col gap-1",
            )
        ),
        cell(
            rx.el.p(
                f"{row['avg_score']:.1f}%",
                class_name="text-xs font-semibold text-slate-700",
            )
        ),
        class_name=row_class(),
    )


def _role_row(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            chip(row["role"], "teal"),
            rx.el.span(
                f"{row['count']} accounts",
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            class_name="flex items-center justify-between gap-2",
        ),
        rx.el.div(progress_bar(row["share"], "navy"), class_name="mt-2"),
        rx.el.p(
            f"{row['share']}% of the registry",
            class_name="mt-1 text-[0.65rem] font-medium text-slate-500",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def admin_analytics_page() -> rx.Component:
    return admin_page(
        "Analytics",
        "Participation and outcome charts",
        "Series computed from enrolment, certificate and assessment result records — no sample data, every point is queried live.",
        AdminAnalyticsState.error_message,
        "",
        rx.el.div(
            metric_tile(
                "Enrolments analysed",
                f"{AdminAnalyticsState.headline['enrolled']:.0f}",
                "clipboard-list",
                "Across participating courses",
            ),
            metric_tile(
                "Completion rate",
                f"{AdminAnalyticsState.headline['completion_rate']:.1f}%",
                "badge-check",
                "Completed enrolments",
            ),
            metric_tile(
                "Certification rate",
                f"{AdminAnalyticsState.headline['certification_rate']:.1f}%",
                "award",
                "Certificates per enrolment",
            ),
            metric_tile(
                "Assessment pass rate",
                f"{AdminAnalyticsState.headline['pass_rate']:.1f}%",
                "percent",
                f"Mean score {AdminAnalyticsState.headline['average_score']:.1f}%",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.el.div(
            rx.el.div(
                panel(
                    "Participation station plot",
                    "Enrolled, completed and certified counts per course, indexed like observation stations.",
                    rx.cond(
                        AdminAnalyticsState.has_participation,
                        _participation_chart(),
                        empty_block(
                            "No participation to plot",
                            "The chart appears once trainees are enrolled in at least one course.",
                            "chart-column",
                        ),
                    ),
                    icon="chart-column",
                ),
                class_name="flex w-full min-w-0 flex-1 flex-col",
            ),
            rx.el.div(
                panel(
                    "Outcome trace",
                    "Pass rate against mean score for every assessment with recorded activity.",
                    rx.cond(
                        AdminAnalyticsState.has_assessment_series,
                        _outcome_chart(),
                        empty_block(
                            "No assessment outcomes yet",
                            "Once attempts are graded the outcome trace is drawn here.",
                            "chart-line",
                        ),
                    ),
                    icon="chart-line",
                ),
                class_name="flex w-full min-w-0 flex-1 flex-col",
            ),
            class_name="flex w-full min-w-0 flex-col gap-6 xl:flex-row",
        ),
        panel(
            "Participation table",
            "The same series in an accessible table, indexed to the chart above.",
            rx.cond(
                AdminAnalyticsState.is_loading,
                loading_rows(3),
                rx.cond(
                    AdminAnalyticsState.has_participation,
                    data_table(
                        table_head(
                            th("#", "hash"),
                            th("Course", "book-open"),
                            th("Enrolled", "users"),
                            th("Completion", "badge-check"),
                            th("Certification", "award"),
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                AdminAnalyticsState.participation,
                                _participation_row,
                            )
                        ),
                    ),
                    empty_block(
                        "Nothing to tabulate",
                        "Participation figures appear as soon as enrolments exist.",
                        "table",
                    ),
                ),
            ),
            icon="table",
        ),
        panel(
            "Assessment outcome table",
            "Attempts, graded results, pass rate and mean score per assessment.",
            rx.cond(
                AdminAnalyticsState.is_loading,
                loading_rows(3),
                rx.cond(
                    AdminAnalyticsState.has_assessment_series,
                    data_table(
                        table_head(
                            th("#", "hash"),
                            th("Assessment", "list-checks"),
                            th("Attempts", "play"),
                            th("Graded", "check"),
                            th("Pass rate", "badge-check"),
                            th("Mean score", "percent"),
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                AdminAnalyticsState.assessment_series,
                                _outcome_row,
                            )
                        ),
                    ),
                    empty_block(
                        "No graded assessments",
                        "Outcome figures appear once trainees submit attempts.",
                        "list-checks",
                    ),
                ),
            ),
            icon="list-checks",
        ),
        panel(
            "Registry composition",
            "Share of accounts by role across the institution.",
            rx.el.div(
                rx.foreach(AdminAnalyticsState.role_mix, _role_row),
                class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-3",
            ),
            icon="pie-chart",
        ),
    )
