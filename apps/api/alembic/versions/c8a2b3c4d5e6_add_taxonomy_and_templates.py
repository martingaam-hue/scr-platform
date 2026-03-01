"""add_taxonomy_and_templates

Revision ID: c8a2b3c4d5e6
Revises: c0merge0c01c05
Create Date: 2026-03-01 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "c8a2b3c4d5e6"
down_revision = "c0merge0c01c05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "industry_taxonomy",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("parent_code", sa.String(50), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_leaf", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("nace_code", sa.String(20), nullable=True),
        sa.Column("gics_code", sa.String(20), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_taxonomy_parent_code", "industry_taxonomy", ["parent_code"])

    op.create_table(
        "financial_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("taxonomy_code", sa.String(50), sa.ForeignKey("industry_taxonomy.code", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("assumptions", JSONB, nullable=False, server_default="{}"),
        sa.Column("revenue_formula", JSONB, nullable=False, server_default="{}"),
        sa.Column("cashflow_model", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("taxonomy_code", "org_id", "name", name="uq_template_name_per_org"),
    )
    op.create_index("ix_financial_templates_taxonomy", "financial_templates", ["taxonomy_code"])

    # Seed taxonomy nodes
    _seed_taxonomy(op)
    # Seed system templates
    _seed_templates(op)


def _seed_taxonomy(op) -> None:
    """Seed renewable energy taxonomy."""
    op.execute("""
        INSERT INTO industry_taxonomy (code, parent_code, name, level, is_leaf, nace_code, meta) VALUES
        -- Level 1: Sectors
        ('RENEW', NULL, 'Renewable Energy', 1, false, 'D35', '{}'),
        ('INFRA', NULL, 'Infrastructure', 1, false, 'F42', '{}'),
        ('IMPACT', NULL, 'Impact Investing', 1, false, NULL, '{}'),
        -- Level 2: Industries under RENEW
        ('RENEW.SOLAR', 'RENEW', 'Solar Energy', 2, false, 'D35.1', '{}'),
        ('RENEW.WIND', 'RENEW', 'Wind Energy', 2, false, 'D35.1', '{}'),
        ('RENEW.STORAGE', 'RENEW', 'Energy Storage', 2, false, 'D35.1', '{}'),
        ('RENEW.HYDRO', 'RENEW', 'Hydropower', 2, false, 'D35.1', '{}'),
        ('RENEW.BIO', 'RENEW', 'Biomass & Bioenergy', 2, false, 'D35.1', '{}'),
        -- Level 3: Sub-industries under RENEW.SOLAR
        ('RENEW.SOLAR.UTIL', 'RENEW.SOLAR', 'Utility-Scale Solar PV', 3, true, 'D35.11', '{"capacity_unit": "MW", "typical_range_mw": [10, 500]}'),
        ('RENEW.SOLAR.ROOFTOP', 'RENEW.SOLAR', 'Rooftop Solar PV', 3, true, 'D35.11', '{"capacity_unit": "kW", "typical_range_mw": [0.005, 1]}'),
        ('RENEW.SOLAR.CSP', 'RENEW.SOLAR', 'Concentrated Solar Power', 3, true, 'D35.11', '{"capacity_unit": "MW", "typical_range_mw": [50, 400]}'),
        -- Level 3: Sub-industries under RENEW.WIND
        ('RENEW.WIND.ONSHORE', 'RENEW.WIND', 'Onshore Wind', 3, true, 'D35.11', '{"capacity_unit": "MW", "typical_range_mw": [10, 500]}'),
        ('RENEW.WIND.OFFSHORE', 'RENEW.WIND', 'Offshore Wind', 3, true, 'D35.11', '{"capacity_unit": "MW", "typical_range_mw": [100, 1000]}'),
        -- Level 3: Sub-industries under RENEW.STORAGE
        ('RENEW.STORAGE.BESS', 'RENEW.STORAGE', 'Battery Energy Storage (BESS)', 3, true, 'D35.1', '{"capacity_unit": "MWh"}'),
        ('RENEW.STORAGE.PUMP', 'RENEW.STORAGE', 'Pumped Hydro Storage', 3, true, 'D35.1', '{"capacity_unit": "MW"}'),
        -- Infrastructure
        ('INFRA.TRANSPORT', 'INFRA', 'Green Transport', 2, false, 'H49', '{}'),
        ('INFRA.TRANSPORT.EV', 'INFRA.TRANSPORT', 'EV Charging Infrastructure', 3, true, 'H49', '{}'),
        -- Impact
        ('IMPACT.AFFORDABLE', 'IMPACT', 'Affordable Housing', 2, true, 'L68', '{}'),
        ('IMPACT.AGRI', 'IMPACT', 'Sustainable Agriculture', 2, true, 'A01', '{}')
        ON CONFLICT (code) DO NOTHING
    """)


def _seed_templates(op) -> None:
    """Seed system financial templates for key leaf nodes."""
    op.execute("""
        INSERT INTO financial_templates (taxonomy_code, org_id, name, is_system, assumptions, revenue_formula, cashflow_model) VALUES
        (
            'RENEW.SOLAR.UTIL',
            NULL,
            'Utility-Scale Solar PV — Standard DCF',
            true,
            '{
                "capacity_mw": {"default": 50, "min": 10, "max": 500, "unit": "MW"},
                "capex_per_mw": {"default": 800000, "min": 500000, "max": 1200000, "unit": "EUR/MW"},
                "opex_per_mw_yr": {"default": 15000, "min": 10000, "max": 25000, "unit": "EUR/MW/yr"},
                "p50_irradiance_kwh_m2": {"default": 1500, "min": 800, "max": 2200, "unit": "kWh/m2/yr"},
                "performance_ratio": {"default": 0.80, "min": 0.70, "max": 0.90},
                "ppa_price_eur_mwh": {"default": 55, "min": 30, "max": 90, "unit": "EUR/MWh"},
                "degradation_pct_yr": {"default": 0.005, "min": 0.003, "max": 0.008},
                "project_life_years": {"default": 25, "min": 20, "max": 30},
                "discount_rate": {"default": 0.07, "min": 0.04, "max": 0.12},
                "debt_pct": {"default": 0.70, "min": 0.50, "max": 0.80}
            }',
            '{"type": "ppa", "formula": "capacity_mw * 1000 * p50_irradiance_kwh_m2 / 1000 * performance_ratio * ppa_price_eur_mwh"}',
            '{"model": "dcf", "capex_year": 1, "construction_years": 1}'
        ),
        (
            'RENEW.WIND.ONSHORE',
            NULL,
            'Onshore Wind — Standard DCF',
            true,
            '{
                "capacity_mw": {"default": 50, "min": 10, "max": 300, "unit": "MW"},
                "capex_per_mw": {"default": 1200000, "min": 900000, "max": 1600000, "unit": "EUR/MW"},
                "opex_per_mw_yr": {"default": 40000, "min": 25000, "max": 60000, "unit": "EUR/MW/yr"},
                "capacity_factor": {"default": 0.35, "min": 0.25, "max": 0.50},
                "ppa_price_eur_mwh": {"default": 50, "min": 35, "max": 80, "unit": "EUR/MWh"},
                "project_life_years": {"default": 25, "min": 20, "max": 30},
                "discount_rate": {"default": 0.075, "min": 0.05, "max": 0.12},
                "debt_pct": {"default": 0.65, "min": 0.50, "max": 0.80}
            }',
            '{"type": "ppa", "formula": "capacity_mw * 8760 * capacity_factor * ppa_price_eur_mwh"}',
            '{"model": "dcf", "capex_year": 1, "construction_years": 2}'
        ),
        (
            'RENEW.STORAGE.BESS',
            NULL,
            'BESS — Merchant/Ancillary Services',
            true,
            '{
                "capacity_mwh": {"default": 100, "min": 10, "max": 500, "unit": "MWh"},
                "power_mw": {"default": 50, "min": 5, "max": 250, "unit": "MW"},
                "capex_per_mwh": {"default": 300000, "min": 200000, "max": 500000, "unit": "EUR/MWh"},
                "opex_per_mwh_yr": {"default": 8000, "min": 5000, "max": 15000, "unit": "EUR/MWh/yr"},
                "cycles_per_day": {"default": 1.5, "min": 0.5, "max": 3.0},
                "revenue_per_mwh_cycle": {"default": 80, "min": 40, "max": 150, "unit": "EUR/MWh"},
                "project_life_years": {"default": 15, "min": 10, "max": 20},
                "discount_rate": {"default": 0.08, "min": 0.05, "max": 0.15}
            }',
            '{"type": "merchant", "formula": "capacity_mwh * cycles_per_day * 365 * revenue_per_mwh_cycle"}',
            '{"model": "dcf", "capex_year": 1, "construction_years": 1}'
        )
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("financial_templates")
    op.drop_table("industry_taxonomy")
