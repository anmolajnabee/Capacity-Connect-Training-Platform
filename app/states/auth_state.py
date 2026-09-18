"""Authentication, session, approval and account management state."""

from __future__ import annotations

import datetime as dt
import os
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import select

from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    PasswordResetToken,
    TraineeProfile,
    TrainerProfile,
    User,
    UserRole,
)
from app.security import (
    generate_reset_token,
    hash_password,
    hash_token,
    password_problem,
    read_session,
    sign_session,
    verify_password,
)
from app.seed import DEMO_ACCOUNTS, ensure_seed_data

logger = logging.getLogger(__name__)

ROLE_HOME: dict[str, str] = {
    UserRole.TRAINEE.value: "/trainee",
    UserRole.TRAINER.value: "/trainer",
    UserRole.ADMIN.value: "/admin",
}

ROLE_PORTAL_LABEL: dict[str, str] = {
    UserRole.TRAINEE.value: "Trainee",
    UserRole.TRAINER.value: "Trainer",
    UserRole.ADMIN.value: "Administrator",
}


class DemoAccount(TypedDict):
    role: str
    email: str
    note: str


class PortalOption(TypedDict):
    role: str
    label: str
    tagline: str
    icon: str
    heading: str
    description: str
    expectations: list[str]
    workspace: list[str]
    pathway: list[str]
    demo_email: str


def _demo_email(role_word: str) -> str:
    for account in DEMO_ACCOUNTS:
        if account["role"].lower() == role_word:
            return account["email"]
    return ""


PORTAL_OPTIONS: list[PortalOption] = [
    {
        "role": UserRole.TRAINEE.value,
        "label": "Trainee",
        "tagline": "Learn, assess, certify",
        "icon": "graduation-cap",
        "heading": "Trainee access",
        "description": (
            "Sign in to your competency record: enrolled courses, structured "
            "study material, assessments, scored results and certificates."
        ),
        "expectations": [
            "Trainee accounts are active immediately after registration.",
            "Only your own enrolments, attempts and certificates are visible.",
            "Assessment attempts are time limited and recorded.",
        ],
        "workspace": [
            "Skill meters & profile completion",
            "Course discovery and enrolment",
            "Assessments, results & certificates",
        ],
        "pathway": ["Verify identity", "Trainee workspace", "Certification"],
        "demo_email": _demo_email("trainee"),
    },
    {
        "role": UserRole.TRAINER.value,
        "label": "Trainer",
        "tagline": "Teach, author, monitor",
        "icon": "presentation",
        "heading": "Trainer access",
        "description": (
            "Sign in to your faculty console: assigned courses, resource "
            "library, assessment authoring and cohort performance."
        ),
        "expectations": [
            "Trainer accounts stay pending until an administrator approves them.",
            "Teachable skills drive course-to-trainer competency matching.",
            "Published resources and assessments are attributed to you.",
        ],
        "workspace": [
            "Course & trainee oversight",
            "Resource library and uploads",
            "Assessment studio with deadlines",
        ],
        "pathway": ["Verify identity", "Approval check", "Trainer workspace"],
        "demo_email": _demo_email("trainer"),
    },
    {
        "role": UserRole.ADMIN.value,
        "label": "Administrator",
        "tagline": "Approve, map, publish",
        "icon": "shield-check",
        "heading": "Administrator access",
        "description": (
            "Sign in to the control centre: approvals, role management, "
            "organisation-wide oversight, analytics and competency mapping."
        ),
        "expectations": [
            "Administrator access is granted only by an existing administrator.",
            "Every approval decision is written to an audit record.",
            "Actions here affect all users, courses and certifications.",
        ],
        "workspace": [
            "Approvals & role management",
            "Participation and performance charts",
            "Competency mapping & announcements",
        ],
        "pathway": ["Verify identity", "Privilege check", "Control centre"],
        "demo_email": _demo_email("admin"),
    },
]


class AuthState(rx.State):
    session_cookie: str = rx.Cookie(
        "",
        name="cc_session",
        max_age=60 * 60 * 24 * 7,
        path="/",
        same_site="lax",
        secure=os.getenv("REFLEX_ENV", "prod") != "dev",
    )

    user_id: int = 0
    email: str = ""
    full_name: str = ""
    phone: str = ""
    role: str = ""
    approval_status: str = ""
    avatar_seed: str = ""
    profile_headline: str = ""
    last_login_display: str = ""

    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""
    reset_link: str = ""
    reset_token_input: str = ""

    demo_accounts: list[DemoAccount] = [
        {
            "role": account["role"],
            "email": account["email"],
            "note": account["note"],
        }
        for account in DEMO_ACCOUNTS
    ]
    login_email_prefill: str = ""

    portal_options: list[PortalOption] = PORTAL_OPTIONS
    selected_portal: str = UserRole.TRAINEE.value
    show_password: bool = False

    @rx.var
    def active_portal(self) -> PortalOption:
        for option in PORTAL_OPTIONS:
            if option["role"] == self.selected_portal:
                return option
        return PORTAL_OPTIONS[0]

    @rx.var
    def password_input_type(self) -> str:
        return "text" if self.show_password else "password"

    @rx.var
    def is_authenticated(self) -> bool:
        return self.user_id > 0

    @rx.var
    def is_approved(self) -> bool:
        return self.approval_status == ApprovalStatus.APPROVED.value

    @rx.var
    def is_trainee(self) -> bool:
        return self.role == UserRole.TRAINEE.value

    @rx.var
    def is_trainer(self) -> bool:
        return self.role == UserRole.TRAINER.value

    @rx.var
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    @rx.var
    def role_label(self) -> str:
        return self.role.capitalize() if self.role else "Guest"

    @rx.var
    def workspace_href(self) -> str:
        return ROLE_HOME.get(self.role, "/account")

    @rx.var
    def initials(self) -> str:
        parts = [part for part in self.full_name.split(" ") if part]
        if not parts:
            return "CC"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return f"{parts[0][0]}{parts[-1][0]}".upper()

    # ------------------------------------------------------------- internals
    def _clear_identity(self) -> None:
        self.user_id = 0
        self.email = ""
        self.full_name = ""
        self.phone = ""
        self.role = ""
        self.approval_status = ""
        self.avatar_seed = ""
        self.profile_headline = ""
        self.last_login_display = ""

    def _apply_user(self, session, user: User) -> None:
        self.user_id = user.id
        self.email = user.email
        self.full_name = user.full_name
        self.phone = user.phone
        self.role = user.role
        self.approval_status = user.approval_status
        self.avatar_seed = user.avatar_seed or user.email
        self.last_login_display = (
            user.last_login_at.strftime("%d %b %Y, %H:%M UTC")
            if user.last_login_at
            else "First session"
        )
        headline = ""
        if user.role == UserRole.TRAINER.value:
            profile = session.scalar(
                select(TrainerProfile).where(TrainerProfile.user_id == user.id)
            )
            if profile:
                headline = f"{profile.designation} · {profile.department}"
        elif user.role == UserRole.TRAINEE.value:
            profile = session.scalar(
                select(TraineeProfile).where(TraineeProfile.user_id == user.id)
            )
            if profile:
                headline = f"{profile.designation} · {profile.station}"
        else:
            headline = "Administrator · Capacity Connect control centre"
        self.profile_headline = headline

    def _load_session(self) -> bool:
        """Refresh identity from the signed cookie. Returns True when valid."""
        ensure_seed_data()
        candidate_id = read_session(self.session_cookie)
        if candidate_id <= 0:
            self._clear_identity()
            return False
        try:
            with rx.session() as session:
                user = session.get(User, candidate_id)
                if (
                    user is None
                    or not user.is_active
                    or user.approval_status
                    not in (
                        ApprovalStatus.APPROVED.value,
                        ApprovalStatus.PENDING.value,
                    )
                ):
                    self.session_cookie = ""
                    self._clear_identity()
                    return False
                self._apply_user(session, user)
                return True
        except Exception as exception:
            logging.exception(f"Error loading session: {exception}")
            self._clear_identity()
            return False

    # ---------------------------------------------------------------- events
    @rx.event
    def hydrate_session(self):
        self._load_session()

    @rx.event
    def clear_messages(self):
        self.error_message = ""
        self.success_message = ""
        self.reset_link = ""

    @rx.event
    def select_portal(self, role: str):
        if role not in ROLE_HOME:
            role = UserRole.TRAINEE.value
        self.selected_portal = role
        self.error_message = ""
        self.success_message = ""
        self.login_email_prefill = ""
        self.show_password = False

    @rx.event
    def toggle_password_visibility(self):
        self.show_password = not self.show_password

    @rx.event
    def redirect_if_authenticated(self):
        if self._load_session():
            return rx.redirect(ROLE_HOME.get(self.role, "/account"))

    # ------------------------------------------------------------- guards
    @rx.event
    def guard(self, required_role: str):
        if not self._load_session():
            return rx.redirect("/login")
        if not self.is_approved:
            return rx.redirect("/account")
        if self.role != required_role:
            return rx.redirect(ROLE_HOME.get(self.role, "/"))
        return None

    @rx.event
    def require_auth(self):
        if not self._load_session():
            return rx.redirect("/login")

    @rx.event
    def require_trainee(self):
        return AuthState.guard(UserRole.TRAINEE.value)

    @rx.event
    def require_trainer(self):
        return AuthState.guard(UserRole.TRAINER.value)

    @rx.event
    def require_admin(self):
        return AuthState.guard(UserRole.ADMIN.value)

    # ------------------------------------------------------------- sign in
    @rx.event
    def handle_login(self, form_data: dict[str, Any]):
        ensure_seed_data()
        self.error_message = ""
        self.success_message = ""
        email = str(form_data.get("email", "")).strip().lower()
        password = str(form_data.get("password", ""))
        expected_role = str(
            form_data.get("expected_role", self.selected_portal)
        ).strip()
        if expected_role not in ROLE_HOME:
            expected_role = UserRole.TRAINEE.value
        self.selected_portal = expected_role
        if not email or not password:
            self.error_message = "Enter both your email and password."
            return
        self.is_loading = True
        yield
        try:
            with rx.session() as session:
                user = session.scalar(
                    select(User).where(User.email == email).with_for_update()
                )
                moment = dt.datetime.now(dt.UTC)
                locked = bool(
                    user and user.locked_until and user.locked_until > moment
                )
                valid = (
                    verify_password(
                        password, user.password_hash, user.password_salt
                    )
                    if user
                    else verify_password(
                        password, "invalid", "unknown-account-timing-salt"
                    )
                )
                if locked or not valid:
                    if locked:
                        self.is_loading = False
                        self.error_message = (
                            "Invalid email or password. Try again later."
                        )
                        return
                    if user is not None:
                        user.failed_login_count = min(
                            user.failed_login_count + 1, 10
                        )
                        if user.failed_login_count >= 5:
                            user.locked_until = moment + dt.timedelta(
                                minutes=15
                            )
                        session.commit()
                    self.is_loading = False
                    self.error_message = (
                        "Invalid email or password. Try again later."
                    )
                    return
                if not user.is_active:
                    self.is_loading = False
                    self.error_message = (
                        "This account is deactivated. Contact an administrator."
                    )
                    return
                if user.approval_status == ApprovalStatus.REJECTED.value:
                    self.is_loading = False
                    self.error_message = "Your access request was declined. Contact an administrator."
                    return
                if user.approval_status == ApprovalStatus.SUSPENDED.value:
                    self.is_loading = False
                    self.error_message = "This account is suspended."
                    return
                if user.role != expected_role:
                    self.is_loading = False
                    self.error_message = (
                        "These credentials are not valid for the "
                        f"{ROLE_PORTAL_LABEL[expected_role]} portal. This "
                        f"account is registered as a "
                        f"{ROLE_PORTAL_LABEL.get(user.role, user.role)}. "
                        "Select the correct portal and try again."
                    )
                    return
                user.failed_login_count = 0
                user.locked_until = None
                user.last_login_at = moment
                session.commit()
                session.refresh(user)
                self._apply_user(session, user)
                self.session_cookie = sign_session(user.id)
                pending = user.approval_status == ApprovalStatus.PENDING.value
                target = (
                    "/account" if pending else ROLE_HOME.get(user.role, "/")
                )
        except Exception as exception:
            logging.exception(f"Error during login: {exception}")
            self.is_loading = False
            self.error_message = "Sign in failed. Please try again."
            return
        self.is_loading = False
        self.login_email_prefill = ""
        self.success_message = f"Welcome back, {self.full_name}."
        return rx.redirect(target)

    @rx.event
    def handle_signup(self, form_data: dict[str, Any]):
        ensure_seed_data()
        self.error_message = ""
        self.success_message = ""
        full_name = str(form_data.get("full_name", "")).strip()
        email = str(form_data.get("email", "")).strip().lower()
        phone = str(form_data.get("phone", "")).strip()
        password = str(form_data.get("password", ""))
        confirm = str(form_data.get("confirm_password", ""))
        requested_role = str(
            form_data.get("role", UserRole.TRAINEE.value)
        ).strip()
        if requested_role not in ROLE_HOME:
            requested_role = UserRole.TRAINEE.value
        if len(full_name) < 3:
            self.error_message = "Enter your full name."
            return
        if "@" not in email or "." not in email:
            self.error_message = "Enter a valid email address."
            return
        problem = password_problem(password, confirm)
        if problem:
            self.error_message = problem
            return
        self.is_loading = True
        yield
        try:
            with rx.session() as session:
                existing = session.scalar(
                    select(User).where(User.email == email)
                )
                if existing is not None:
                    self.is_loading = False
                    self.error_message = (
                        "An account with this email already exists."
                    )
                    return
                password_hash, salt = hash_password(password)
                approval = (
                    ApprovalStatus.APPROVED.value
                    if requested_role == UserRole.TRAINEE.value
                    else ApprovalStatus.PENDING.value
                )
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=password_hash,
                    password_salt=salt,
                    password_updated_at=dt.datetime.now(dt.UTC),
                    role=requested_role,
                    approval_status=approval,
                    phone=phone,
                    avatar_seed=email,
                )
                session.add(user)
                session.flush()
                if requested_role == UserRole.TRAINEE.value:
                    session.add(
                        TraineeProfile(user_id=user.id, profile_completion=20)
                    )
                else:
                    session.add(
                        TrainerProfile(
                            user_id=user.id,
                            profile_completion=15,
                            is_available=False,
                        )
                    )
                    session.add(
                        ApprovalRequest(
                            user_id=user.id,
                            requested_role=requested_role,
                            status=ApprovalStatus.PENDING.value,
                            note="Self-registered access request.",
                        )
                    )
                session.commit()
                session.refresh(user)
                self._apply_user(session, user)
                self.session_cookie = sign_session(user.id)
                pending = approval == ApprovalStatus.PENDING.value
        except Exception as exception:
            logging.exception(f"Error during signup: {exception}")
            self.is_loading = False
            self.error_message = "Could not create the account. Try again."
            return
        self.is_loading = False
        if pending:
            self.success_message = (
                "Account created. An administrator must approve your "
                f"{requested_role} access before the workspace opens."
            )
            return rx.redirect("/account")
        self.success_message = "Account created. Welcome to Capacity Connect."
        return rx.redirect("/trainee")

    @rx.event
    def logout(self):
        self.session_cookie = ""
        self._clear_identity()
        self.success_message = "You have been signed out."
        return rx.redirect("/")

    # -------------------------------------------------------- password reset
    @rx.event
    def request_password_reset(self, form_data: dict[str, Any]):
        ensure_seed_data()
        self.error_message = ""
        self.success_message = ""
        self.reset_link = ""
        email = str(form_data.get("email", "")).strip().lower()
        if "@" not in email:
            self.error_message = "Enter a valid email address."
            return
        self.is_loading = True
        yield
        link = ""
        try:
            with rx.session() as session:
                user = session.scalar(select(User).where(User.email == email))
                if user is not None:
                    token, token_hash = generate_reset_token()
                    session.add(
                        PasswordResetToken(
                            user_id=user.id,
                            token_hash=token_hash,
                            expires_at=dt.datetime.now(dt.UTC)
                            + dt.timedelta(hours=2),
                        )
                    )
                    session.commit()
                    link = f"/reset-password?token={token}"
        except Exception as exception:
            logging.exception(f"Error requesting password reset: {exception}")
            self.is_loading = False
            self.error_message = "Could not start the reset. Try again."
            return
        self.is_loading = False
        self.reset_link = ""
        self.success_message = "If that email is registered, contact your administrator for secure account recovery."

    @rx.event
    def load_reset_token(self):
        self.error_message = ""
        self.success_message = ""
        self.reset_token_input = str(
            self.router.url.query_parameters.get("token", "")
        )
        if not self.reset_token_input:
            self.error_message = (
                "This reset link is missing its token. Request a new link."
            )

    @rx.event
    def confirm_password_reset(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        token = str(form_data.get("token", "")) or self.reset_token_input
        password = str(form_data.get("password", ""))
        confirm = str(form_data.get("confirm_password", ""))
        if not token:
            self.error_message = "Reset token missing. Request a new link."
            return
        problem = password_problem(password, confirm)
        if problem:
            self.error_message = problem
            return
        self.is_loading = True
        yield
        try:
            with rx.session() as session:
                record = session.scalar(
                    select(PasswordResetToken).where(
                        PasswordResetToken.token_hash == hash_token(token)
                    )
                )
                now = dt.datetime.now(dt.UTC)
                if (
                    record is None
                    or record.used_at is not None
                    or record.expires_at < now
                ):
                    self.is_loading = False
                    self.error_message = (
                        "This reset link is invalid or has expired."
                    )
                    return
                user = session.get(User, record.user_id)
                if user is None:
                    self.is_loading = False
                    self.error_message = "Account no longer exists."
                    return
                password_hash, salt = hash_password(password)
                user.password_hash = password_hash
                user.password_salt = salt
                user.password_updated_at = now
                user.failed_login_count = 0
                record.used_at = now
                session.commit()
        except Exception as exception:
            logging.exception(f"Error confirming password reset: {exception}")
            self.is_loading = False
            self.error_message = "Could not reset the password. Try again."
            return
        self.is_loading = False
        self.reset_token_input = ""
        self.success_message = (
            "Password updated. You can now sign in with your new password."
        )
        return rx.redirect("/login")

    # ------------------------------------------------------ account settings
    @rx.event
    def update_account(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        if not self._load_session():
            return rx.redirect("/login")
        full_name = str(form_data.get("full_name", "")).strip()
        phone = str(form_data.get("phone", "")).strip()
        if len(full_name) < 3:
            self.error_message = "Enter your full name."
            return
        try:
            with rx.session() as session:
                user = session.get(User, self.user_id)
                if user is None:
                    self.error_message = "Account not found."
                    return
                user.full_name = full_name
                user.phone = phone
                session.commit()
                session.refresh(user)
                self._apply_user(session, user)
        except Exception as exception:
            logging.exception(f"Error updating account: {exception}")
            self.error_message = "Could not save your details. Try again."
            return
        self.success_message = "Account details saved."

    @rx.event
    def change_password(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        if not self._load_session():
            return rx.redirect("/login")
        current = str(form_data.get("current_password", ""))
        password = str(form_data.get("password", ""))
        confirm = str(form_data.get("confirm_password", ""))
        problem = password_problem(password, confirm)
        if problem:
            self.error_message = problem
            return
        try:
            with rx.session() as session:
                user = session.get(User, self.user_id)
                if user is None or not verify_password(
                    current, user.password_hash, user.password_salt
                ):
                    self.error_message = "Current password is incorrect."
                    return
                password_hash, salt = hash_password(password)
                user.password_hash = password_hash
                user.password_salt = salt
                user.password_updated_at = dt.datetime.now(dt.UTC)
                session.commit()
        except Exception as exception:
            logging.exception(f"Error changing password: {exception}")
            self.error_message = "Could not change the password. Try again."
            return
        self.success_message = "Password changed successfully."
