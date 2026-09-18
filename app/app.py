import reflex as rx
from app.services.email_notifications import email_worker

from app.components.capacity_workspace import (
    competency_page,
    registry_page,
    reports_page,
    verification_page,
)
from app.states.competency_workspace_state import CompetencyWorkspaceState
from app.states.registry_workspace_state import RegistryWorkspaceState
from app.states.certificate_verification_state import (
    CertificateVerificationState,
)

from app.pages.about import about_page
from app.pages.account import account_page
from app.pages.admin_analytics import admin_analytics_page
from app.pages.admin_announcements import admin_announcements_page
from app.pages.admin_competency import admin_competency_page
from app.pages.admin_courses import admin_courses_page, admin_trainers_page
from app.pages.admin_dashboard import admin_dashboard_page
from app.pages.admin_records import (
    admin_assessments_page,
    admin_certifications_page,
)
from app.pages.admin_users import (
    admin_approvals_page,
    admin_roles_page,
    admin_users_page,
)
from app.pages.announcements import announcements_page
from app.pages.auth_pages import (
    forgot_password_page,
    login_page,
    reset_password_page,
    signup_page,
)
from app.pages.courses import courses_page
from app.pages.home import home_page
from app.pages.trainee_assessments import trainee_assessments_page
from app.pages.trainee_assignments import trainee_assignments_page
from app.pages.trainee_courses import trainee_courses_page
from app.pages.trainee_dashboard import trainee_dashboard_page
from app.pages.trainee_learning import (
    trainee_learning_page,
    trainee_resources_page,
)
from app.pages.trainee_profile import trainee_profile_page
from app.pages.trainee_records import (
    trainee_certificates_page,
    trainee_feedback_page,
    trainee_results_page,
)
from app.pages.trainer_assignments import trainer_assignments_page
from app.pages.trainer_courses import (
    trainer_courses_page,
    trainer_trainees_page,
)
from app.pages.trainer_dashboard import trainer_dashboard_page
from app.pages.trainer_library import (
    trainer_library_page,
    trainer_upload_page,
)
from app.pages.trainer_performance import trainer_performance_page
from app.pages.trainer_profile import trainer_profile_page
from app.pages.trainer_studio import trainer_studio_page
from app.pages.trainers import trainers_page
from app.states.admin_analytics_state import AdminAnalyticsState
from app.states.admin_announcement_state import AdminAnnouncementState
from app.states.admin_certification_state import AdminCertificationState
from app.states.admin_competency_state import AdminCompetencyState
from app.states.admin_course_ops_state import AdminCourseOpsState
from app.states.admin_role_ops_state import AdminRoleOpsState
from app.states.admin_oversight_state import AdminOversightState
from app.states.admin_state import AdminState
from app.states.auth_state import AuthState
from app.states.public_state import PublicState
from app.states.trainee_assessment_state import TraineeAssessmentState
from app.states.trainee_assignment_state import TraineeAssignmentState
from app.states.trainee_certification_state import TraineeCertificationState
from app.states.trainee_learning_state import TraineeLearningState
from app.states.trainee_state import TraineeState
from app.states.trainer_assessment_state import TrainerAssessmentState
from app.states.trainer_assignment_workflow_state import (
    TrainerAssignmentWorkflowState,
)
from app.states.trainer_course_state import TrainerCourseState
from app.states.trainer_resource_state import TrainerResourceState
from app.states.trainer_state import TrainerState


def index() -> rx.Component:
    return home_page()


app = rx.App(
    theme=rx.theme(appearance="light"),
    stylesheets=["/theme.css"],
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(
            rel="preconnect",
            href="https://fonts.gstatic.com",
            cross_origin="",
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)

app.register_lifespan_task(email_worker)

# Public routes
app.add_page(
    index,
    route="/",
    title="CAPACITY CONNECT — Institutional capacity building registry",
    description="Competency-first training registry connecting courses, trainers, resources, assessments and certification.",
    on_load=[PublicState.load_public_content, AuthState.hydrate_session],
)
app.add_page(
    about_page,
    route="/about",
    title="About — CAPACITY CONNECT",
    on_load=[PublicState.load_public_content, AuthState.hydrate_session],
)
app.add_page(
    courses_page,
    route="/courses",
    title="Courses — CAPACITY CONNECT",
    on_load=[PublicState.load_public_content, AuthState.hydrate_session],
)
app.add_page(
    trainers_page,
    route="/trainers",
    title="Trainers — CAPACITY CONNECT",
    on_load=[PublicState.load_public_content, AuthState.hydrate_session],
)
app.add_page(
    announcements_page,
    route="/announcements",
    title="Announcements — CAPACITY CONNECT",
    on_load=[PublicState.load_public_content, AuthState.hydrate_session],
)

# Authentication routes
app.add_page(
    login_page,
    route="/login",
    title="Sign in — CAPACITY CONNECT",
    on_load=AuthState.clear_messages,
)
app.add_page(
    signup_page,
    route="/signup",
    title="Register — CAPACITY CONNECT",
    on_load=AuthState.clear_messages,
)
app.add_page(
    forgot_password_page,
    route="/forgot-password",
    title="Forgot password — CAPACITY CONNECT",
    on_load=AuthState.clear_messages,
)
app.add_page(
    reset_password_page,
    route="/reset-password",
    title="Reset password — CAPACITY CONNECT",
    on_load=AuthState.load_reset_token,
)
app.add_page(
    account_page,
    route="/account",
    title="Account — CAPACITY CONNECT",
    on_load=AuthState.require_auth,
)

# Role-guarded workspaces
app.add_page(
    trainee_dashboard_page,
    route="/trainee",
    title="Trainee dashboard — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, TraineeState.load_dashboard],
)
app.add_page(
    trainee_profile_page,
    route="/trainee/profile",
    title="Trainee profile — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, TraineeState.load_profile_workspace],
)
app.add_page(
    trainee_courses_page,
    route="/trainee/courses",
    title="Course discovery — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, TraineeLearningState.load_discovery],
)
app.add_page(
    trainee_learning_page,
    route="/trainee/learning",
    title="My learning — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, TraineeLearningState.load_my_learning],
)
app.add_page(
    trainee_resources_page,
    route="/trainee/resources",
    title="Learning resources — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, TraineeLearningState.load_my_learning],
)
app.add_page(
    trainee_assessments_page,
    route="/trainee/assessments",
    title="Assessments — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        TraineeAssessmentState.load_assessments,
    ],
)
app.add_page(
    trainee_assignments_page,
    route="/trainee/assignments",
    title="Assignments — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        TraineeAssignmentState.load_assignments,
    ],
)
app.add_page(
    trainee_results_page,
    route="/trainee/results",
    title="Results — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        TraineeAssessmentState.load_results,
        TraineeAssessmentState.load_certificates,
    ],
)
app.add_page(
    trainee_certificates_page,
    route="/trainee/certificates",
    title="Certificates — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        TraineeAssessmentState.load_certificates,
        TraineeCertificationState.load_readiness,
    ],
)
app.add_page(
    trainee_feedback_page,
    route="/trainee/feedback",
    title="Course feedback — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, TraineeLearningState.load_feedback],
)
app.add_page(
    trainer_dashboard_page,
    route="/trainer",
    title="Trainer workspace — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerState.load_dashboard],
)
app.add_page(
    trainer_profile_page,
    route="/trainer/profile",
    title="Expertise profile — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerState.load_profile],
)
app.add_page(
    trainer_courses_page,
    route="/trainer/courses",
    title="My courses — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerCourseState.load_courses],
)
app.add_page(
    trainer_trainees_page,
    route="/trainer/trainees",
    title="Trainees — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerCourseState.load_courses],
)
app.add_page(
    trainer_library_page,
    route="/trainer/library",
    title="Trainer library — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerResourceState.load_library],
)
app.add_page(
    trainer_upload_page,
    route="/trainer/upload",
    title="Upload content — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerResourceState.load_library],
)
app.add_page(
    trainer_studio_page,
    route="/trainer/assessments/create",
    title="Create assessment — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerAssessmentState.load_studio],
)
app.add_page(
    trainer_assignments_page,
    route="/trainer/assignments",
    title="Assignments & grading — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        TrainerAssignmentWorkflowState.load_workspace,
    ],
)
app.add_page(
    trainer_performance_page,
    route="/trainer/performance",
    title="Cohort performance — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, TrainerCourseState.load_courses],
)
app.add_page(
    admin_dashboard_page,
    route="/admin",
    title="Admin control centre — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, AdminState.load_control_centre],
)
app.add_page(
    admin_users_page,
    route="/admin/users",
    title="Users — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, AdminState.load_control_centre],
)
app.add_page(
    admin_approvals_page,
    route="/admin/approvals",
    title="Approvals — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, AdminState.load_control_centre],
)
app.add_page(
    admin_roles_page,
    route="/admin/roles",
    title="Role management — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        AdminState.load_control_centre,
        AdminRoleOpsState.load_role_operations,
    ],
)
app.add_page(
    admin_courses_page,
    route="/admin/courses",
    title="Courses — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        AdminOversightState.load_oversight,
        AdminCourseOpsState.load_course_ops,
    ],
)
app.add_page(
    admin_trainers_page,
    route="/admin/trainers",
    title="Trainers — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        AdminOversightState.load_oversight,
        AdminCourseOpsState.load_course_ops,
    ],
)
app.add_page(
    admin_assessments_page,
    route="/admin/assessments",
    title="Assessments — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, AdminOversightState.load_oversight],
)
app.add_page(
    admin_certifications_page,
    route="/admin/certifications",
    title="Certifications — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        AdminOversightState.load_oversight,
        AdminCertificationState.load_requests,
    ],
)
app.add_page(
    admin_analytics_page,
    route="/admin/analytics",
    title="Analytics — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, AdminAnalyticsState.load_analytics],
)
app.add_page(
    admin_announcements_page,
    route="/admin/announcements",
    title="Announcements — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        AdminAnnouncementState.load_announcements,
    ],
)
app.add_page(
    admin_competency_page,
    route="/admin/legacy-skill-matching",
    title="Legacy skill compatibility — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, AdminCompetencyState.load_courses],
)


def _competency_view(role: str, active: str, title: str):
    def page() -> rx.Component:
        return competency_page(role, active, title)

    return page


def _registry_view(role: str, active: str, title: str, description: str):
    def page() -> rx.Component:
        return registry_page(role, active, title, description)

    return page


app.add_page(
    _competency_view(
        "trainee", "Competencies", "Competencies & development gaps"
    ),
    route="/trainee/competencies",
    title="Competencies — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, CompetencyWorkspaceState.load],
)
app.add_page(
    _competency_view("trainee", "Competency Passport", "Competency passport"),
    route="/trainee/passport",
    title="Competency passport — CAPACITY CONNECT",
    on_load=[AuthState.require_trainee, CompetencyWorkspaceState.load],
)
app.add_page(
    _competency_view("trainer", "Competencies", "Verified expertise record"),
    route="/trainer/competencies",
    title="Verified expertise — CAPACITY CONNECT",
    on_load=[AuthState.require_trainer, CompetencyWorkspaceState.load],
)
app.add_page(
    _competency_view("admin", "Competencies", "Organizational competency map"),
    route="/admin/competencies",
    title="Organizational competency map — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, CompetencyWorkspaceState.load],
)
app.add_page(
    _competency_view("admin", "Competencies", "Organizational competency map"),
    route="/admin/competency",
    title="Organizational competency map — CAPACITY CONNECT",
    on_load=[AuthState.require_admin, CompetencyWorkspaceState.load],
)
app.add_page(
    _registry_view(
        "trainee",
        "Practice",
        "Practice history",
        "Start weak-competency practice, save responses and review feedback. Practice stays separate from official assessment results.",
    ),
    route="/trainee/practice",
    title="Practice history — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        RegistryWorkspaceState.open_view("practice"),
    ],
)
app.add_page(
    _registry_view(
        "trainee",
        "Learning Paths",
        "Personal learning paths",
        "Follow the ordered steps recorded for your competency development.",
    ),
    route="/trainee/paths",
    title="Learning paths — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        RegistryWorkspaceState.open_view("paths"),
    ],
)
app.add_page(
    _registry_view(
        "trainee",
        "Notifications",
        "Notifications",
        "Your direct, role, course and organizational notices.",
    ),
    route="/trainee/notifications",
    title="Notifications — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainee,
        RegistryWorkspaceState.open_view("notifications"),
    ],
)
app.add_page(
    _registry_view(
        "trainer",
        "Notifications",
        "Notifications",
        "Notices relevant to your approved trainer role and assigned courses.",
    ),
    route="/trainer/notifications",
    title="Trainer notifications — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        RegistryWorkspaceState.open_view("notifications"),
    ],
)
app.add_page(
    _registry_view(
        "trainer",
        "Training Programs",
        "Training programs",
        "Program → Course → Module → Lesson. Only your currently approved course assignments are included.",
    ),
    route="/trainer/programs",
    title="Training programs — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        RegistryWorkspaceState.open_view("programs"),
    ],
)
app.add_page(
    _registry_view(
        "trainer",
        "Participation",
        "Cohort participation",
        "Enrollment, completion, risk and progress aggregated from your assigned courses.",
    ),
    route="/trainer/participation",
    title="Participation — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        RegistryWorkspaceState.open_view("participation"),
    ],
)
app.add_page(
    _registry_view(
        "trainer",
        "Feedback",
        "Training feedback",
        "Recorded course feedback for your assigned courses. Anonymous respondents remain anonymous.",
    ),
    route="/trainer/feedback",
    title="Trainer feedback — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        RegistryWorkspaceState.open_view("feedback"),
    ],
)
app.add_page(
    _registry_view(
        "trainer",
        "Availability",
        "Availability & capacity",
        "Add or update your availability and capacity windows. Use the same start/end timestamps to update a window; missing capacity is never unlimited.",
    ),
    route="/trainer/availability",
    title="Trainer availability — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        RegistryWorkspaceState.open_view("availability"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Trainer Fit",
        "Trainer Fit Score ledger",
        "Saved, explainable evaluations with the exact factors and weights used at evaluation time.",
    ),
    route="/admin/trainer-fit",
    title="Trainer Fit Score — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("trainer-fit"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Team Coverage",
        "Team competency coverage",
        "Inspect saved team proposals, members and explicit covered or missing competencies.",
    ),
    route="/admin/team-matches",
    title="Trainer team coverage — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("teams"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Requirements",
        "Capacity & competency requirements",
        "Normalized organizational needs, professional role targets and course requirements.",
    ),
    route="/admin/requirements",
    title="Competency requirements — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("requirements"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Participation",
        "Training participation",
        "Current participation and completion across the training registry.",
    ),
    route="/admin/participation",
    title="Training participation — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("participation"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Effectiveness",
        "Observed training effectiveness",
        "Verified pre/post competency observations, official results, participation and learner feedback.",
    ),
    route="/admin/effectiveness",
    title="Observed training effectiveness — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("effectiveness"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Learning Content",
        "Structured learning content",
        "Publish structured learning content and review the program delivery hierarchy without replacing legacy course records.",
    ),
    route="/admin/learning-content",
    title="Learning content — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("learning-content"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Achievements",
        "Achievement registry",
        "Recorded achievement criteria, active status and award counts. No impact claims are inferred.",
    ),
    route="/admin/achievements",
    title="Achievements — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("achievements"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Notifications",
        "Administrative notifications",
        "Current notices addressed to your role and memberships.",
    ),
    route="/admin/notifications",
    title="Admin notifications — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("notifications"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Settings",
        "Organizational framework registry",
        "Organizations, departments, professional roles, subjects and structured competencies. Existing authentication settings remain under Account.",
    ),
    route="/admin/settings",
    title="Organizational framework — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("framework"),
    ],
)
app.add_page(
    reports_page,
    route="/admin/reports",
    title="Operational reports — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("participation"),
    ],
)
app.add_page(
    verification_page,
    route="/verify/[certificate_id]",
    title="Verify certificate — CAPACITY CONNECT",
    on_load=CertificateVerificationState.load,
)
app.add_page(
    _registry_view(
        "trainer",
        "Create Training",
        "Create Training",
        "Author draft programs, courses, modules and lessons within your approved trainer scope. Review AI-generated formative drafts before publication.",
    ),
    route="/trainer/create-training",
    title="Create Training — CAPACITY CONNECT",
    on_load=[
        AuthState.require_trainer,
        RegistryWorkspaceState.open_view("programs"),
    ],
)
app.add_page(
    _registry_view(
        "admin",
        "Trainees",
        "Trainee enrollment & evidence",
        "Enrollment, completion, open development gaps and verified competency counts from current records.",
    ),
    route="/admin/trainees",
    title="Trainees — CAPACITY CONNECT",
    on_load=[
        AuthState.require_admin,
        RegistryWorkspaceState.open_view("trainees"),
    ],
)
