"""Tests for the ProcessingJob domain state machine."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.documents.jobs import JobType, ProcessingJob
from app.domain.shared.exceptions import ValidationError
from app.shared.constants import ProcessingJobStatus


def _job() -> ProcessingJob:
    return ProcessingJob(
        id=uuid4(),
        document_id=uuid4(),
        tenant_id="t",
        job_type=JobType.DOCUMENT_INGESTION,
    )


def test_initial_state_is_queued() -> None:
    job = _job()
    assert job.status == ProcessingJobStatus.QUEUED
    assert job.is_active
    assert not job.is_terminal


def test_start_transitions_to_running() -> None:
    job = _job()
    job.start("worker-1")
    assert job.status == ProcessingJobStatus.RUNNING
    assert job.worker_name == "worker-1"
    assert job.started_at is not None


def test_cannot_start_non_queued() -> None:
    job = _job()
    job.start("w")
    with pytest.raises(ValidationError):
        job.start("w")


def test_advance_through_phases() -> None:
    job = _job()
    job.start("w")
    job.advance(ProcessingJobStatus.PARSING, 20)
    assert job.status == ProcessingJobStatus.PARSING
    assert job.progress == 20
    job.advance(ProcessingJobStatus.CHUNKING, 60)
    assert job.progress == 60


def test_advance_rejects_non_phase_status() -> None:
    job = _job()
    job.start("w")
    with pytest.raises(ValidationError):
        job.advance(ProcessingJobStatus.COMPLETED, 100)


def test_complete_is_terminal() -> None:
    job = _job()
    job.start("w")
    job.complete()
    assert job.status == ProcessingJobStatus.COMPLETED
    assert job.progress == 100
    assert job.is_terminal
    assert job.finished_at is not None


def test_fail_records_error() -> None:
    job = _job()
    job.start("w")
    job.fail("boom")
    assert job.status == ProcessingJobStatus.FAILED
    assert job.error_message == "boom"
    assert job.is_terminal


def test_cannot_complete_after_terminal() -> None:
    job = _job()
    job.start("w")
    job.fail("x")
    with pytest.raises(ValidationError):
        job.complete()


def test_retry_requeues_and_increments() -> None:
    job = _job()
    job.start("w")
    job.fail("x")
    assert job.can_retry(max_retries=3)
    job.retry()
    assert job.status == ProcessingJobStatus.QUEUED
    assert job.retry_count == 1
    assert job.error_message is None
    assert job.started_at is None


def test_can_retry_respects_limit() -> None:
    job = _job()
    job.retry_count = 3
    job.start("w")
    job.fail("x")
    assert not job.can_retry(max_retries=3)


def test_cancel_is_terminal() -> None:
    job = _job()
    job.cancel()
    assert job.status == ProcessingJobStatus.CANCELLED
    assert job.is_terminal
