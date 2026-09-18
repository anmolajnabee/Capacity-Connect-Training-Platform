import reflex as rx
from app.states.admin_announcement_state import AdminAnnouncementState as State


def delivery_row(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(row["event"], class_name="font-semibold text-[#0A1B33]"),
            rx.el.p(row["recipient"], class_name="break-all text-slate-600"),
        ),
        rx.el.div(
            rx.el.p(row["status"], class_name="font-semibold text-teal-700"),
            rx.el.p(
                f"Attempts: {row['attempts']}", class_name="text-slate-600"
            ),
        ),
        rx.el.div(
            rx.el.p(f"Scheduled: {row['scheduled']}"),
            rx.el.p(f"Accepted: {row['accepted']}"),
            class_name="text-slate-600",
        ),
        rx.el.div(
            rx.el.p(row["error"], class_name="text-amber-800"),
            rx.cond(
                (
                    (row["status"] == "blocked")
                    | (row["status"] == "retry")
                    | (row["status"] == "failed")
                )
                & (row["error"] != "acceptance_unknown"),
                rx.el.button(
                    "Retry",
                    on_click=State.retry_email_delivery(row["id"]),
                    disabled=State.email_loading,
                    class_name="mt-2 rounded border border-teal-600 bg-white px-3 py-1 text-teal-700 hover:bg-teal-50 disabled:opacity-50",
                ),
                rx.fragment(),
            ),
        ),
        class_name="grid grid-cols-1 gap-3 border-t border-slate-200 bg-white p-3 text-xs md:grid-cols-4",
        key=row["id"],
    )


def email_ledger() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Email delivery ledger",
                class_name="text-lg font-semibold text-[#0A1B33]",
            ),
            rx.el.button(
                rx.icon("send", class_name="size-4"),
                "Process pending",
                on_click=State.dispatch_pending_email,
                disabled=State.email_loading,
                class_name="flex items-center gap-2 rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white hover:bg-teal-600 disabled:opacity-50",
            ),
            class_name="flex flex-wrap items-center justify-between gap-3",
        ),
        rx.el.p(
            "Accepted means accepted by Resend — not proof of delivery or opening.",
            class_name="mt-2 text-xs text-slate-600",
        ),
        rx.el.p(
            f"Configuration: {State.email_configuration}",
            class_name="mt-2 text-xs text-amber-800",
        ),
        rx.el.p(
            State.email_message,
            role="status",
            class_name="mt-2 text-xs text-teal-800",
        ),
        rx.el.div(
            rx.foreach(
                [
                    "pending",
                    "sending",
                    "accepted",
                    "retry",
                    "blocked",
                    "failed",
                ],
                lambda status: rx.el.div(
                    rx.el.p(status, class_name="text-xs text-slate-600"),
                    rx.el.p(
                        State.delivery_metrics[status],
                        class_name="text-lg font-semibold text-[#0A1B33]",
                    ),
                    class_name="rounded border border-slate-200 bg-slate-50 p-3",
                ),
            ),
            class_name="my-4 grid grid-cols-2 gap-2 md:grid-cols-6",
        ),
        rx.cond(
            State.email_loading,
            rx.el.p(
                "Loading delivery records…",
                class_name="animate-pulse p-4 text-sm text-slate-600",
            ),
            rx.cond(
                State.delivery_records.length() > 0,
                rx.el.div(rx.foreach(State.delivery_records, delivery_row)),
                rx.el.p(
                    "No email events have been queued yet.",
                    class_name="p-4 text-sm text-slate-600",
                ),
            ),
        ),
        rx.el.p(
            "Most recent 50 records. Counts include the full ledger. Unknown acceptance is held for reconciliation rather than risking a duplicate.",
            class_name="mt-3 text-xs text-slate-500",
        ),
        class_name="w-full overflow-hidden rounded-xl border border-slate-200 bg-white p-5",
    )
