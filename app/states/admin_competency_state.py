"""Competency mapping: weighted course skills ranked against trainer expertise."""

from __future__ import annotations

import logging
from typing import TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    ApprovalStatus,
    Course,
    CourseRequiredSkill,
    CourseTrainerAssignment,
    Enrollment,
    ProficiencyLevel,
    Skill,
    TrainerAssignmentRole,
    TrainerProfile,
    User,
    UserRole,
    UserSkill,
)
from app.states.admin_state import admin_guard

logger = logging.getLogger(__name__)

LEVEL_TARGET: dict[str, int] = {
    ProficiencyLevel.BEGINNER.value: 40,
    ProficiencyLevel.INTERMEDIATE.value: 60,
    ProficiencyLevel.ADVANCED.value: 75,
    ProficiencyLevel.EXPERT.value: 90,
}


class CourseChoice(TypedDict):
    id: int
    code: str
    title: str
    status: str
    skills: int
    trainers: int


class RequiredSkillRow(TypedDict):
    skill_id: int
    name: str
    category: str
    minimum_level: str
    target: int
    weight: float
    weight_share: int
    mandatory: bool


class SkillCell(TypedDict):
    skill_id: int
    name: str
    score: int
    target: int
    level: str
    met: bool


class TrainerMatch(TypedDict):
    trainer_id: int
    name: str
    email: str
    designation: str
    department: str
    specialization: str
    years: float
    rating: float
    available: bool
    score: float
    weighted_average: float
    matched_count: int
    required_count: int
    coverage: int
    matched: list[str]
    gaps: list[str]
    cells: list[SkillCell]
    is_assigned: bool
    assignment_role: str
    load: int
    recommended: bool


class AdminCompetencyState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    courses: list[CourseChoice] = []
    selected_course_id: int = 0
    selected_course_label: str = ""
    required_skills: list[RequiredSkillRow] = []
    matches: list[TrainerMatch] = []
    total_weight: float = 0.0

    @rx.var
    def has_course(self) -> bool:
        return self.selected_course_id > 0

    @rx.var
    def assignable_matches(self) -> list[TrainerMatch]:
        return [row for row in self.matches if not row["is_assigned"]]

    @rx.var
    def assigned_matches(self) -> list[TrainerMatch]:
        return [row for row in self.matches if row["is_assigned"]]

    @rx.var
    def top_score(self) -> float:
        if not self.matches:
            return 0.0
        return self.matches[0]["score"]

    @rx.event
    async def load_courses(self):
        self.error_message = ""
        if await admin_guard(self) == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                rows = (
                    await session.execute(select(Course).order_by(Course.code))
                ).scalars()
                choices: list[CourseChoice] = []
                for course in rows:
                    skills = int(
                        await session.scalar(
                            select(func.count())
                            .select_from(CourseRequiredSkill)
                            .where(CourseRequiredSkill.course_id == course.id)
                        )
                        or 0
                    )
                    trainers = int(
                        await session.scalar(
                            select(func.count())
                            .select_from(CourseTrainerAssignment)
                            .where(
                                CourseTrainerAssignment.course_id == course.id
                            )
                        )
                        or 0
                    )
                    choices.append(
                        {
                            "id": course.id,
                            "code": course.code,
                            "title": course.title,
                            "status": course.status,
                            "skills": skills,
                            "trainers": trainers,
                        }
                    )
                self.courses = choices
                if self.selected_course_id == 0 and choices:
                    self.selected_course_id = choices[0]["id"]
        except Exception as exception:
            logging.exception(f"Error loading mapping courses: {exception}")
            self.error_message = "Could not load the course list."
            self.is_loading = False
            return
        self.is_loading = False
        if self.selected_course_id > 0:
            yield AdminCompetencyState.compute_matches

    @rx.event
    async def select_course(self, course_id: int):
        self.selected_course_id = course_id
        self.success_message = ""
        return AdminCompetencyState.compute_matches

    @rx.event
    async def compute_matches(self):
        self.error_message = ""
        if await admin_guard(self) == 0:
            self.error_message = "Administrator access is required."
            return
        if self.selected_course_id == 0:
            self.required_skills = []
            self.matches = []
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._compute(session, self.selected_course_id)
        except Exception as exception:
            logging.exception(f"Error computing competency map: {exception}")
            self.error_message = "Could not compute trainer match scores."
        self.is_loading = False

    async def _compute(self, session, course_id: int) -> None:
        course = await session.get(Course, course_id)
        if course is None:
            self.error_message = "That course no longer exists."
            self.required_skills = []
            self.matches = []
            return
        self.selected_course_label = f"{course.code} · {course.title}"
        pairs = (
            await session.execute(
                select(CourseRequiredSkill, Skill)
                .join(Skill, Skill.id == CourseRequiredSkill.skill_id)
                .where(CourseRequiredSkill.course_id == course_id)
                .order_by(CourseRequiredSkill.weight.desc())
            )
        ).all()
        total_weight = sum(float(row.weight) for row, _skill in pairs)
        self.total_weight = total_weight
        self.required_skills = [
            {
                "skill_id": skill.id,
                "name": skill.name,
                "category": skill.category or "General",
                "minimum_level": requirement.minimum_level,
                "target": LEVEL_TARGET.get(requirement.minimum_level, 50),
                "weight": float(requirement.weight),
                "weight_share": int(
                    round(float(requirement.weight) * 100 / total_weight)
                )
                if total_weight
                else 0,
                "mandatory": bool(requirement.is_mandatory),
            }
            for requirement, skill in pairs
        ]
        if not pairs:
            self.matches = []
            return

        assignments = {
            row.trainer_id: row
            for row in (
                (
                    await session.execute(
                        select(CourseTrainerAssignment).where(
                            CourseTrainerAssignment.course_id == course_id
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        trainer_rows = (
            await session.execute(
                select(User, TrainerProfile)
                .outerjoin(TrainerProfile, TrainerProfile.user_id == User.id)
                .where(
                    User.role == UserRole.TRAINER.value,
                    User.approval_status == ApprovalStatus.APPROVED.value,
                    User.is_active.is_(True),
                )
                .order_by(User.full_name)
            )
        ).all()
        matches: list[TrainerMatch] = []
        for user, profile in trainer_rows:
            skills = {
                row.skill_id: row
                for row in (
                    (
                        await session.execute(
                            select(UserSkill).where(
                                UserSkill.user_id == user.id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            }
            weighted_sum = 0.0
            matched: list[str] = []
            gaps: list[str] = []
            cells: list[SkillCell] = []
            for requirement in self.required_skills:
                held = skills.get(requirement["skill_id"])
                score = int(held.proficiency_score) if held else 0
                level = held.level if held else "not recorded"
                met = score >= requirement["target"]
                weighted_sum += score * requirement["weight"]
                if met:
                    matched.append(f"{requirement['name']} · {score}%")
                else:
                    gaps.append(
                        f"{requirement['name']} · {score}% of {requirement['target']}%"
                    )
                cells.append(
                    {
                        "skill_id": requirement["skill_id"],
                        "name": requirement["name"],
                        "score": score,
                        "target": requirement["target"],
                        "level": level,
                        "met": met,
                    }
                )
            weighted_average = (
                weighted_sum / total_weight if total_weight else 0.0
            )
            coverage = (
                int(round(len(matched) * 100 / len(self.required_skills)))
                if self.required_skills
                else 0
            )
            load = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .join(
                        CourseTrainerAssignment,
                        CourseTrainerAssignment.course_id
                        == Enrollment.course_id,
                    )
                    .where(CourseTrainerAssignment.trainer_id == user.id)
                )
                or 0
            )
            assignment = assignments.get(user.id)
            matches.append(
                {
                    "trainer_id": user.id,
                    "name": user.full_name,
                    "email": user.email,
                    "designation": profile.designation
                    if profile
                    else "Profile pending",
                    "department": profile.department if profile else "—",
                    "specialization": profile.specialization
                    if profile
                    else "—",
                    "years": float(profile.years_of_training)
                    if profile
                    else 0.0,
                    "rating": float(profile.rating_average) if profile else 0.0,
                    "available": bool(profile.is_available)
                    if profile
                    else False,
                    "score": round(weighted_average, 1),
                    "weighted_average": round(weighted_average, 1),
                    "matched_count": len(matched),
                    "required_count": len(self.required_skills),
                    "coverage": coverage,
                    "matched": matched,
                    "gaps": gaps,
                    "cells": cells,
                    "is_assigned": assignment is not None,
                    "assignment_role": assignment.assignment_role.replace(
                        "_", " "
                    )
                    if assignment
                    else "—",
                    "load": load,
                    "recommended": False,
                }
            )
        matches.sort(key=lambda row: row["score"], reverse=True)
        for position, row in enumerate(matches):
            row["recommended"] = position == 0 and row["score"] > 0
        self.matches = matches
        # Persist recomputed scores for existing assignments so the trainer
        # workspace reflects the current competency evidence.
        try:
            async with rx.asession() as write_session:
                for row in matches:
                    if not row["is_assigned"]:
                        continue
                    record = await write_session.scalar(
                        select(CourseTrainerAssignment).where(
                            CourseTrainerAssignment.course_id == course_id,
                            CourseTrainerAssignment.trainer_id
                            == row["trainer_id"],
                        )
                    )
                    if record is not None:
                        record.match_score = float(row["score"])
                await write_session.commit()
        except Exception as exception:
            logging.exception(f"Error persisting match scores: {exception}")

    @rx.event
    async def assign_trainer(self, trainer_id: int):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = (
                "Only an approved administrator may assign trainers."
            )
            return
        if self.selected_course_id == 0:
            self.error_message = "Select a course first."
            return
        score = 0.0
        matched = 0
        required = 0
        for row in self.matches:
            if row["trainer_id"] == trainer_id:
                score = float(row["score"])
                matched = row["matched_count"]
                required = row["required_count"]
        try:
            async with rx.asession() as session:
                existing = await session.scalar(
                    select(CourseTrainerAssignment).where(
                        CourseTrainerAssignment.course_id
                        == self.selected_course_id,
                        CourseTrainerAssignment.trainer_id == trainer_id,
                    )
                )
                if existing is not None:
                    self.error_message = (
                        "That trainer is already assigned to this course."
                    )
                    return
                leads = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(CourseTrainerAssignment)
                        .where(
                            CourseTrainerAssignment.course_id
                            == self.selected_course_id,
                            CourseTrainerAssignment.assignment_role
                            == TrainerAssignmentRole.LEAD.value,
                        )
                    )
                    or 0
                )
                session.add(
                    CourseTrainerAssignment(
                        course_id=self.selected_course_id,
                        trainer_id=trainer_id,
                        assignment_role=TrainerAssignmentRole.CO_TRAINER.value
                        if leads
                        else TrainerAssignmentRole.LEAD.value,
                        status=ApprovalStatus.APPROVED.value,
                        match_score=score,
                        assigned_by_id=admin_id,
                        notes=(
                            f"Competency match {score:.1f}% with {matched} of "
                            f"{required} required skills met."
                        ),
                    )
                )
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error assigning trainer: {exception}")
            self.error_message = "Could not assign that trainer. Try again."
            return
        self.success_message = (
            f"Trainer assigned with a persisted match score of {score:.1f}%."
        )
        return AdminCompetencyState.compute_matches

    @rx.event
    async def remove_assignment(self, trainer_id: int):
        self.error_message = ""
        self.success_message = ""
        if await admin_guard(self) == 0:
            self.error_message = (
                "Only an approved administrator may change assignments."
            )
            return
        try:
            async with rx.asession() as session:
                record = await session.scalar(
                    select(CourseTrainerAssignment).where(
                        CourseTrainerAssignment.course_id
                        == self.selected_course_id,
                        CourseTrainerAssignment.trainer_id == trainer_id,
                    )
                )
                if record is None:
                    self.error_message = "That assignment no longer exists."
                    return
                await session.delete(record)
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error removing assignment: {exception}")
            self.error_message = "Could not remove that assignment."
            return
        self.success_message = "Assignment removed."
        return AdminCompetencyState.compute_matches
