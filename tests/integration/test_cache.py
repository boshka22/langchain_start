"""Интеграционные тесты кэширования и Celery таска."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.v1.resume import (
    AnalysisStatus,
    CriteriaScore,
    ResumeAnalysisResponse,
)

MOCK_ANALYSIS = ResumeAnalysisResponse(
    status=AnalysisStatus.success,
    overall_score=8,
    summary='Хорошее резюме.',
    criteria={
        'skills': CriteriaScore(score=8, feedback='Хорошо.', suggestions=['Улучшить']),
        'experience': CriteriaScore(score=8, feedback='Хорошо.', suggestions=['Улучшить']),
        'structure': CriteriaScore(score=8, feedback='Хорошо.', suggestions=['Улучшить']),
        'language': CriteriaScore(score=8, feedback='Хорошо.', suggestions=['Улучшить']),
    },
    top_strengths=['Стек', 'Опыт', 'Язык'],
    top_improvements=['Summary', 'Версии', 'Клише'],
    file_name='resume.txt',
)


@pytest.mark.asyncio
async def test_analyze_cache_miss(client: AsyncClient) -> None:
    """Первый запрос — кэша нет, таск ставится в очередь."""
    mock_task = MagicMock()
    mock_task.id = 'test-task-uuid-123'

    with (
        patch('app.cache.resume.ResumeCache.get', new_callable=AsyncMock, return_value=None),
        patch('app.cache.resume.ResumeCache.close', new_callable=AsyncMock),
        patch('app.tasks.analyze.analyze_resume_task.delay', return_value=mock_task),
    ):
        response = await client.post(
            '/api/v1/resume/analyze',
            files={'file': ('resume.txt', b'Python developer ' * 20, 'text/plain')},
        )

    assert response.status_code == 202
    data = response.json()
    assert data['cached'] is False
    assert data['task_id'] == 'test-task-uuid-123'
    assert data['status'] == 'pending'
    assert response.headers.get('x-cache') == 'MISS'


@pytest.mark.asyncio
async def test_analyze_cache_hit(client: AsyncClient) -> None:
    """Второй запрос — кэш есть, результат возвращается мгновенно."""
    with (
        patch(
            'app.cache.resume.ResumeCache.get', new_callable=AsyncMock, return_value=MOCK_ANALYSIS
        ),
        patch('app.cache.resume.ResumeCache.close', new_callable=AsyncMock),
    ):
        response = await client.post(
            '/api/v1/resume/analyze',
            files={'file': ('resume.txt', b'Python developer ' * 20, 'text/plain')},
        )

    assert response.status_code == 202
    data = response.json()
    assert data['cached'] is True
    assert data['task_id'] == 'cached'
    assert data['status'] == 'success'
    assert data['result'] is not None
    assert data['result']['overall_score'] == 8
    assert response.headers.get('x-cache') == 'HIT'


@pytest.mark.asyncio
async def test_analyze_returns_result_on_cache_hit(client: AsyncClient) -> None:
    """При кэш-хите результат приходит сразу, поллинг не нужен."""
    with (
        patch(
            'app.cache.resume.ResumeCache.get', new_callable=AsyncMock, return_value=MOCK_ANALYSIS
        ),
        patch('app.cache.resume.ResumeCache.close', new_callable=AsyncMock),
    ):
        response = await client.post(
            '/api/v1/resume/analyze',
            files={'file': ('resume.txt', b'Python developer ' * 20, 'text/plain')},
        )

    data = response.json()
    result = data['result']
    assert result['status'] == 'success'
    assert 'criteria' in result
    assert 'skills' in result['criteria']
    assert 'top_strengths' in result
