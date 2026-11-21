"""diagnose(): ask First Domino to start a diagnosis of a run, and wait for its verdict."""

import asyncio
from uuid import UUID

from first_domino._generated.models import CreateDiagnosisRequest, Diagnosis, DiagnosisStatus
from first_domino.client import FirstDominoClient, default_client

_FINAL_STATUSES = frozenset({DiagnosisStatus.done, DiagnosisStatus.failed})


async def diagnose(run_id: UUID, *, client: FirstDominoClient | None = None) -> Diagnosis:
    """Start a diagnosis of a failed recorded run and return it as it starts.

    Raises:
        ConfigurationError: `FIRST_DOMINO_API_KEY` is not set.
        ApiRequestError: The API refused, for example `conflict` while one already runs.

    Example:
        >>> diagnosis = await fd.diagnose(run.run_id)
    """
    api = client or default_client()
    return await api.create_diagnosis(CreateDiagnosisRequest(run_id=run_id))


async def wait_for_diagnosis(
    diagnosis_id: UUID, *, client: FirstDominoClient | None = None
) -> Diagnosis:
    """Poll a diagnosis until it is `done` or `failed`. Wrap in `asyncio.timeout` to bound it.

    Example:
        >>> async with asyncio.timeout(600):
        ...     final = await fd.wait_for_diagnosis(diagnosis.id)
        >>> final.first_domino_step
        4
    """
    api = client or default_client()
    while True:
        diagnosis = await api.get_diagnosis(diagnosis_id)
        if diagnosis.status in _FINAL_STATUSES:
            return diagnosis
        await asyncio.sleep(api.settings.diagnosis_poll_seconds)
