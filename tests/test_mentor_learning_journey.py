"""MENTOR minimal learning-journey smoke test.

Exercise the actual FastAPI + SQLAlchemy + local-document code path:
course creation -> Markdown upload -> content tree -> seeded, source-linked
QCM -> answer submission -> persisted result and FSRS progress.

Question *generation* by an LLM is intentionally outside this deterministic
test: its content validation needs separate mock-provider and corpus gates.
No external network access and no code-execution sandbox are required.
"""

import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import settings
from database import Base, get_db
from main import app
from models.content import CourseContentTree
from models.practice import PracticeProblem, PracticeResult
from models.progress import LearningProgress
from models.user import User
from services.auth.dependency import get_current_user


@pytest_asyncio.fixture
async def learning_client(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "mentor-learning.sqlite3"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}", poolclass=NullPool
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    user_id = uuid.uuid4()
    async with session_factory() as db:
        db.add(User(id=user_id, name="MENTOR Integration Learner"))
        await db.commit()

    async def override_db():
        async with session_factory() as db:
            yield db

    async def override_user(request: Request):
        request.state.user_id = str(user_id)
        request.state.deployment_mode = "single_user"
        return User(id=user_id, name="MENTOR Integration Learner")

    # Existing uploader suppresses its external embedding job for in-process
    # ASGI tests when this state flag is present.
    original_test_factory = getattr(app.state, "test_session_factory", None)
    was_set = hasattr(app.state, "test_session_factory")
    app.state.test_session_factory = session_factory

    # The existing ingestion dispatcher schedules LLM autogeneration even
    # during tests. Cancel these tasks: this test only verifies document
    # ingestion and the persisted quiz/learning state.
    monkeypatch.setattr(
        "services.agent.background_runtime.track_background_task",
        lambda task: task.cancel(),
    )
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    old_db_override = app.dependency_overrides.get(get_db)
    old_user_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://mentor.test"
        ) as client:
            yield client, session_factory, user_id
    finally:
        if old_db_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = old_db_override
        if old_user_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = old_user_override
        if was_set:
            app.state.test_session_factory = original_test_factory
        else:
            delattr(app.state, "test_session_factory")
        await engine.dispose()


@pytest.mark.asyncio
async def test_document_to_quiz_to_persisted_learning_progress(learning_client):
    client, session_factory, user_id = learning_client

    created = await client.post(
        "/api/courses/",
        json={"name": "Préparation concours 2027", "description": "Demo source"},
    )
    assert created.status_code == 201, created.text
    course_id = created.json()["id"]

    source = (
        "# Organisation de la gendarmerie\n\n"
        "Le texte de démonstration présente un chapitre de cours. "
        "Il contient plusieurs notions pour vérifier l'extraction et "
        "la création d'un arbre documentaire dans MENTOR.\n\n"
        "## Compétences\n\nLe candidat répond à des questions sourcées.\n"
    )
    uploaded = await client.post(
        "/api/content/upload",
        data={"course_id": course_id},
        files={"file": ("organisation.md", source.encode("utf-8"), "text/markdown")},
    )
    assert uploaded.status_code == 200, uploaded.text
    upload_data = uploaded.json()
    assert upload_data["status"] == "ok"
    assert upload_data["nodes_created"] >= 1
    assert upload_data["course_id"] == course_id

    tree_resp = await client.get(f"/api/courses/{course_id}/content-tree")
    assert tree_resp.status_code == 200, tree_resp.text
    assert tree_resp.json(), "Imported course must contain content nodes"

    jobs = await client.get(f"/api/content/jobs/{course_id}")
    assert jobs.status_code == 200, jobs.text
    assert any(j["id"] == upload_data["job_id"] for j in jobs.json())

    async with session_factory() as db:
        node = (
            await db.execute(
                select(CourseContentTree)
                .where(CourseContentTree.course_id == uuid.UUID(course_id))
                .order_by(CourseContentTree.order_index)
                .limit(1)
            )
        ).scalar_one()

        question = PracticeProblem(
            course_id=uuid.UUID(course_id),
            content_node_id=node.id,
            question_type="mc",
            question="Quel nombre fait 2 + 2 ?",
            options={"a": "3", "b": "4"},
            correct_answer="4",
            explanation="2 + 2 = 4.",
            source="user",
            order_index=0,
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)
        question_id = question.id

    listed = await client.get(f"/api/quiz/{course_id}")
    assert listed.status_code == 200, listed.text
    assert any(x["id"] == str(question_id) for x in listed.json())

    answered = await client.post(
        "/api/quiz/submit",
        json={"problem_id": str(question_id), "user_answer": "4", "answer_time_ms": 2300},
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["is_correct"] is True

    async with session_factory() as db:
        result = (
            await db.execute(
                select(PracticeResult).where(
                    PracticeResult.problem_id == question_id,
                    PracticeResult.user_id == user_id,
                )
            )
        ).scalar_one()
        assert result.user_answer == "4"
        assert result.is_correct is True

        progress = (
            await db.execute(
                select(LearningProgress).where(
                    LearningProgress.user_id == user_id,
                    LearningProgress.course_id == uuid.UUID(course_id),
                    LearningProgress.content_node_id == node.id,
                )
            )
        ).scalar_one()
        assert progress.quiz_attempts == 1
        assert progress.quiz_correct == 1
        assert progress.fsrs_reps >= 1
        assert progress.next_review_at is not None
