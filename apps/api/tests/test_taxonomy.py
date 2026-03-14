"""Tests for the taxonomy module: NACE/GICS classification lookup, tree structure, HTTP endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taxonomy import IndustryTaxonomy
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio


# ── Fixtures / helpers ────────────────────────────────────────────────────────


async def _seed_taxonomy(db: AsyncSession) -> list[IndustryTaxonomy]:
    """Insert a minimal NACE/GICS-aligned taxonomy tree for testing.

    Tree shape:
        A  (level 1, sector, not leaf)
        ├── A.1  (level 2, industry, not leaf)
        │   ├── A.1.1  (level 3, sub-industry, leaf)
        │   └── A.1.2  (level 3, sub-industry, leaf)
        └── A.2  (level 2, industry, leaf)
        B  (level 1, sector, not leaf)
        └── B.1  (level 2, industry, leaf)

    Codes use a UUID suffix to avoid collisions with C08 migration seeds.
    """
    suffix = uuid.uuid4().hex[:6]
    energy = f"TEST-ENERGY-{suffix}"
    energy_renew = f"TEST-ENERGY.RENEW-{suffix}"
    energy_renew_solar = f"TEST-ENERGY.RENEW.SOLAR-{suffix}"
    energy_renew_wind = f"TEST-ENERGY.RENEW.WIND-{suffix}"
    energy_fossil = f"TEST-ENERGY.FOSSIL-{suffix}"
    infra = f"TEST-INFRA-{suffix}"
    infra_transport = f"TEST-INFRA.TRANSPORT-{suffix}"

    nodes = [
        IndustryTaxonomy(
            code=energy,
            parent_code=None,
            name="Energy",
            description="Energy sector (NACE D)",
            level=1,
            is_leaf=False,
            nace_code="D",
            gics_code="10",
            meta={},
        ),
        IndustryTaxonomy(
            code=energy_renew,
            parent_code=energy,
            name="Renewable Energy",
            description="Wind, solar, hydro",
            level=2,
            is_leaf=False,
            nace_code="D35.1",
            gics_code="10102010",
            meta={"unit_hint": "MWh"},
        ),
        IndustryTaxonomy(
            code=energy_renew_solar,
            parent_code=energy_renew,
            name="Solar Power",
            description="Photovoltaic and concentrated solar",
            level=3,
            is_leaf=True,
            nace_code="D35.11",
            gics_code="10102015",
            meta={},
        ),
        IndustryTaxonomy(
            code=energy_renew_wind,
            parent_code=energy_renew,
            name="Wind Power",
            description="Onshore and offshore wind",
            level=3,
            is_leaf=True,
            nace_code="D35.12",
            gics_code="10102020",
            meta={},
        ),
        IndustryTaxonomy(
            code=energy_fossil,
            parent_code=energy,
            name="Fossil Fuels",
            description="Oil, gas, coal",
            level=2,
            is_leaf=True,
            nace_code="D35.2",
            gics_code="10102030",
            meta={},
        ),
        IndustryTaxonomy(
            code=infra,
            parent_code=None,
            name="Infrastructure",
            description="Infrastructure sector",
            level=1,
            is_leaf=False,
            nace_code="F",
            gics_code="20",
            meta={},
        ),
        IndustryTaxonomy(
            code=infra_transport,
            parent_code=infra,
            name="Transport Infrastructure",
            description="Roads, ports, rail",
            level=2,
            is_leaf=True,
            nace_code="H49",
            gics_code="20202010",
            meta={},
        ),
    ]
    for node in nodes:
        db.add(node)
    await db.flush()
    # Attach the generated codes as attributes for test reference
    nodes[0]._test_code = energy
    nodes[1]._test_code = energy_renew
    nodes[2]._test_code = energy_renew_solar
    nodes[3]._test_code = energy_renew_wind
    nodes[4]._test_code = energy_fossil
    nodes[5]._test_code = infra
    nodes[6]._test_code = infra_transport
    return nodes


# ── Service/DB-level tests ────────────────────────────────────────────────────


async def test_taxonomy_seed_creates_nodes(db: AsyncSession, sample_org, sample_user):
    """Seeded taxonomy nodes are persisted and queryable."""
    from sqlalchemy import select

    nodes = await _seed_taxonomy(db)
    result = await db.execute(
        select(IndustryTaxonomy).where(IndustryTaxonomy.is_deleted.is_(False))
    )
    stored = result.scalars().all()
    stored_codes = {n.code for n in stored}

    for node in nodes:
        assert node.code in stored_codes


async def test_taxonomy_nace_gics_fields_stored(db: AsyncSession, sample_org, sample_user):
    """NACE and GICS codes are stored and retrievable per node."""
    from sqlalchemy import select

    nodes = await _seed_taxonomy(db)
    solar_code = nodes[2].code  # ENERGY.RENEW.SOLAR node

    result = await db.execute(
        select(IndustryTaxonomy).where(IndustryTaxonomy.code == solar_code)
    )
    node = result.scalar_one_or_none()

    assert node is not None
    assert node.nace_code == "D35.11"
    assert node.gics_code == "10102015"
    assert node.is_leaf is True
    assert node.level == 3


async def test_taxonomy_tree_parent_child_relationship(db: AsyncSession, sample_org, sample_user):
    """Children are correctly linked via parent_code."""
    from sqlalchemy import select

    nodes = await _seed_taxonomy(db)
    energy_renew_code = nodes[1].code  # ENERGY.RENEW node
    energy_renew_solar_code = nodes[2].code
    energy_renew_wind_code = nodes[3].code

    result = await db.execute(
        select(IndustryTaxonomy)
        .where(IndustryTaxonomy.parent_code == energy_renew_code)
        .where(IndustryTaxonomy.is_deleted.is_(False))
        .order_by(IndustryTaxonomy.code)
    )
    children = result.scalars().all()

    assert len(children) == 2
    child_codes = {c.code for c in children}
    assert child_codes == {energy_renew_solar_code, energy_renew_wind_code}


async def test_taxonomy_leaf_only_filter(db: AsyncSession, sample_org, sample_user):
    """Leaf nodes (is_leaf=True) can be filtered correctly."""
    from sqlalchemy import select

    nodes = await _seed_taxonomy(db)
    energy_renew_solar_code = nodes[2].code
    energy_renew_wind_code = nodes[3].code
    energy_fossil_code = nodes[4].code
    infra_transport_code = nodes[6].code
    energy_code = nodes[0].code
    energy_renew_code = nodes[1].code

    result = await db.execute(
        select(IndustryTaxonomy)
        .where(IndustryTaxonomy.is_leaf.is_(True))
        .where(IndustryTaxonomy.is_deleted.is_(False))
    )
    leaves = result.scalars().all()

    leaf_codes = {n.code for n in leaves}
    # Known leaves from our seed
    assert energy_renew_solar_code in leaf_codes
    assert energy_renew_wind_code in leaf_codes
    assert energy_fossil_code in leaf_codes
    assert infra_transport_code in leaf_codes
    # Non-leaves must be excluded
    assert energy_code not in leaf_codes
    assert energy_renew_code not in leaf_codes


async def test_taxonomy_sector_level_nodes(db: AsyncSession, sample_org, sample_user):
    """Level 1 nodes represent top-level sectors."""
    from sqlalchemy import select

    nodes = await _seed_taxonomy(db)
    energy_code = nodes[0].code
    infra_code = nodes[5].code
    energy_renew_solar_code = nodes[2].code

    result = await db.execute(
        select(IndustryTaxonomy)
        .where(IndustryTaxonomy.level == 1)
        .where(IndustryTaxonomy.is_deleted.is_(False))
        .order_by(IndustryTaxonomy.code)
    )
    sectors = result.scalars().all()

    sector_codes = {n.code for n in sectors}
    assert energy_code in sector_codes
    assert infra_code in sector_codes
    # No sub-industry should appear at level 1
    assert energy_renew_solar_code not in sector_codes


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_list_taxonomy_returns_all_nodes(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/taxonomy returns all non-deleted nodes."""
    nodes = await _seed_taxonomy(db)
    energy_code = nodes[0].code
    energy_renew_solar_code = nodes[2].code

    resp = await authenticated_client.get("/v1/taxonomy")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 7  # we seeded 7
    codes = [n["code"] for n in data]
    assert energy_code in codes
    assert energy_renew_solar_code in codes


async def test_http_list_taxonomy_filter_by_parent(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/taxonomy?parent_code=ENERGY.RENEW returns direct children only."""
    nodes = await _seed_taxonomy(db)
    energy_renew_code = nodes[1].code
    energy_renew_solar_code = nodes[2].code
    energy_renew_wind_code = nodes[3].code
    energy_code = nodes[0].code

    resp = await authenticated_client.get("/v1/taxonomy", params={"parent_code": energy_renew_code})

    assert resp.status_code == 200
    data = resp.json()
    returned_codes = [n["code"] for n in data]
    assert energy_renew_solar_code in returned_codes
    assert energy_renew_wind_code in returned_codes
    # Grandparent must not appear
    assert energy_code not in returned_codes


async def test_http_list_taxonomy_leaf_only(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/taxonomy?leaf_only=true returns only leaf nodes."""
    await _seed_taxonomy(db)

    resp = await authenticated_client.get("/v1/taxonomy", params={"leaf_only": "true"})

    assert resp.status_code == 200
    data = resp.json()
    assert all(n["is_leaf"] is True for n in data)


async def test_http_get_taxonomy_node_by_code(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/taxonomy/{code} returns full node including gics_code."""
    nodes = await _seed_taxonomy(db)
    energy_renew_code = nodes[1].code  # Renewable Energy node

    resp = await authenticated_client.get(f"/v1/taxonomy/{energy_renew_code}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == energy_renew_code
    assert data["name"] == "Renewable Energy"
    assert data["nace_code"] == "D35.1"
    assert data["gics_code"] == "10102010"
    assert data["level"] == 2
    assert data["is_leaf"] is False
    assert "meta" in data


async def test_http_get_taxonomy_node_404_for_unknown_code(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/taxonomy/{unknown_code} returns 404."""
    resp = await authenticated_client.get("/v1/taxonomy/DOES.NOT.EXIST")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
