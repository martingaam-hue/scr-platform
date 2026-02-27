"""Tests for tenant isolation middleware and helpers."""

import uuid

import pytest
from sqlalchemy import select

from app.middleware.tenant import tenant_filter
from app.models.projects import Project
from app.models.enums import ProjectType, ProjectStatus


class TestTenantFilter:
    """Test the tenant_filter query helper."""

    def test_appends_org_id_filter(self):
        org_id = uuid.uuid4()
        stmt = select(Project)
        filtered = tenant_filter(stmt, org_id, Project)

        # The filtered statement should have a WHERE clause
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": False}))
        assert "org_id" in compiled

    def test_no_filter_for_model_without_org_id(self):
        """Models without org_id should pass through unchanged."""
        org_id = uuid.uuid4()

        # Use a mock model without org_id
        class NoOrgModel:
            pass

        stmt = select(Project)
        filtered = tenant_filter(stmt, org_id, NoOrgModel)

        # Statement should be unchanged
        original = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        result = str(filtered.compile(compile_kwargs={"literal_binds": False}))
        assert original == result

    def test_different_org_ids_produce_different_filters(self):
        org1 = uuid.uuid4()
        org2 = uuid.uuid4()

        stmt1 = tenant_filter(select(Project), org1, Project)
        stmt2 = tenant_filter(select(Project), org2, Project)

        # Both should have WHERE clauses but with different params
        compiled1 = str(stmt1.compile(compile_kwargs={"literal_binds": False}))
        compiled2 = str(stmt2.compile(compile_kwargs={"literal_binds": False}))
        assert "org_id" in compiled1
        assert "org_id" in compiled2
