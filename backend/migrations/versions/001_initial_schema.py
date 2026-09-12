"""Initial schema with PostGIS and 8 core tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-11 00:00:00.000000

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Create Enums
    user_role = ENUM("analyst", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)

    breach_type = ENUM("structural", "landslide_glof", name="breach_type", create_type=False)
    breach_type.create(op.get_bind(), checkfirst=True)

    run_status = ENUM(
        "pending", "running", "succeeded", "failed", name="run_status", create_type=False
    )
    run_status.create(op.get_bind(), checkfirst=True)

    pipeline_stage = ENUM(
        "dem_fetch",
        "breach_estimation",
        "flood_routing",
        "summary_generation",
        name="pipeline_stage",
        create_type=False,
    )
    pipeline_stage.create(op.get_bind(), checkfirst=True)

    export_format = ENUM("pdf", "json", name="export_format", create_type=False)
    export_format.create(op.get_bind(), checkfirst=True)

    # 3. Create 'users' table
    op.create_table(
        "users",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="analyst"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # 4. Create 'scenarios' table
    op.create_table(
        "scenarios",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "site_point",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("breach_type", breach_type, nullable=False),
        sa.Column("dam_height_m", sa.Numeric(8, 2), nullable=False),
        sa.Column("dam_volume_m3", sa.Numeric(14, 2), nullable=False),
        sa.Column("simulation_radius_km", sa.Numeric(6, 2), nullable=False, server_default="25.0"),
        sa.Column(
            "is_dem_estimated", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("dam_height_m > 0", name="chk_dam_height_positive"),
        sa.CheckConstraint("dam_volume_m3 > 0", name="chk_dam_volume_positive"),
        sa.CheckConstraint("simulation_radius_km > 0", name="chk_sim_radius_positive"),
    )
    op.create_index("idx_scenarios_user_id", "scenarios", ["user_id"])
    op.create_index(
        "idx_scenarios_site_point", "scenarios", ["site_point"], postgresql_using="gist"
    )

    # 5. Create 'simulation_runs' table
    op.create_table(
        "simulation_runs",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "scenario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", run_status, nullable=False, server_default="pending"),
        sa.Column("current_stage", pipeline_stage, nullable=True),
        sa.Column("error_stage", pipeline_stage, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_simulation_runs_scenario_id", "simulation_runs", ["scenario_id"])
    op.create_index("idx_simulation_runs_status", "simulation_runs", ["status"])

    # 6. Create 'flood_results' table
    op.create_table(
        "flood_results",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "simulation_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("time_step_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "flood_extent",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("max_depth_m", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("simulation_run_id", "time_step_minutes", name="uq_run_timestep"),
        sa.CheckConstraint("time_step_minutes >= 0", name="chk_timestep_nonnegative"),
    )
    op.create_index(
        "idx_flood_results_run_timestep",
        "flood_results",
        ["simulation_run_id", "time_step_minutes"],
    )
    op.create_index(
        "idx_flood_results_flood_extent", "flood_results", ["flood_extent"], postgresql_using="gist"
    )

    # 7. Create 'settlements' reference table
    op.create_table(
        "settlements",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("district", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_settlements_location", "settlements", ["location"], postgresql_using="gist"
    )

    # 8. Create 'affected_settlements' table
    op.create_table(
        "affected_settlements",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "simulation_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "settlement_id",
            UUID(as_uuid=True),
            sa.ForeignKey("settlements.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("arrival_time_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_depth_m", sa.Numeric(6, 2), nullable=True),
        sa.UniqueConstraint("simulation_run_id", "settlement_id", name="uq_run_settlement"),
        sa.CheckConstraint("arrival_time_minutes >= 0", name="chk_arrival_nonnegative"),
    )
    op.create_index(
        "idx_affected_settlements_run_id", "affected_settlements", ["simulation_run_id"]
    )

    # 9. Create 'case_studies' table
    op.create_table(
        "case_studies",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "scenario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "simulation_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("simulation_runs.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("event_year", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # 10. Create 'exports' table
    op.create_table(
        "exports",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "simulation_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("format", export_format, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_exports_user_id", "exports", ["user_id"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("exports")
    op.drop_table("case_studies")
    op.drop_table("affected_settlements")
    op.drop_table("settlements")
    op.drop_table("flood_results")
    op.drop_table("simulation_runs")
    op.drop_table("scenarios")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS export_format;")
    op.execute("DROP TYPE IF EXISTS pipeline_stage;")
    op.execute("DROP TYPE IF EXISTS run_status;")
    op.execute("DROP TYPE IF EXISTS breach_type;")
    op.execute("DROP TYPE IF EXISTS user_role;")
