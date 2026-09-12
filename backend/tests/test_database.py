"""Tests for Database Schema, Alembic Migrations, and Seed Data Integrity."""

import os
import sys

import bcrypt
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.models import (  # noqa: E402
    AffectedSettlement,
    Base,
    BreachType,
    ExportFormat,
    FloodResult,
    PipelineStage,
    RunStatus,
    Scenario,
    SimulationRun,
    UserRole,
)
from backend.seed.seed_case_studies import (  # noqa: E402
    seed_case_studies,
)
from backend.seed.seed_settlements import seed_settlements  # noqa: E402
from backend.seed.seed_system_user import ANALYST_USER_ID, SYSTEM_USER_ID, seed_users  # noqa: E402


class TestSchemaDefinitions:
    """Verify that SQLAlchemy models match the Database Schema specification exactly."""

    def test_all_8_tables_registered_in_metadata(self):
        expected_tables = {
            "users",
            "scenarios",
            "simulation_runs",
            "flood_results",
            "settlements",
            "affected_settlements",
            "case_studies",
            "exports",
        }
        actual_tables = set(Base.metadata.tables.keys())
        assert expected_tables.issubset(actual_tables), (
            f"Missing tables: {expected_tables - actual_tables}"
        )

    def test_user_table_schema(self):
        table = Base.metadata.tables["users"]
        assert "id" in table.c
        assert "email" in table.c
        assert "password_hash" in table.c
        assert "role" in table.c
        assert "created_at" in table.c
        assert "updated_at" in table.c
        assert table.c.email.unique is True

    def test_scenario_table_schema_and_constraints(self):
        table = Base.metadata.tables["scenarios"]
        expected_cols = [
            "id",
            "user_id",
            "name",
            "site_point",
            "breach_type",
            "dam_height_m",
            "dam_volume_m3",
            "simulation_radius_km",
            "is_dem_estimated",
            "created_at",
            "updated_at",
        ]
        for col in expected_cols:
            assert col in table.c

        # Verify check constraints
        constraint_names = {c.name for c in table.constraints if hasattr(c, "name")}
        assert "chk_dam_height_positive" in constraint_names
        assert "chk_dam_volume_positive" in constraint_names
        assert "chk_sim_radius_positive" in constraint_names

    def test_simulation_run_table_schema(self):
        table = Base.metadata.tables["simulation_runs"]
        expected_cols = [
            "id",
            "scenario_id",
            "status",
            "current_stage",
            "error_stage",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
        ]
        for col in expected_cols:
            assert col in table.c

    def test_flood_result_table_schema_and_constraints(self):
        table = Base.metadata.tables["flood_results"]
        expected_cols = [
            "id",
            "simulation_run_id",
            "time_step_minutes",
            "flood_extent",
            "max_depth_m",
            "created_at",
        ]
        for col in expected_cols:
            assert col in table.c

        constraint_names = {c.name for c in table.constraints if hasattr(c, "name")}
        assert "uq_run_timestep" in constraint_names
        assert "chk_timestep_nonnegative" in constraint_names

    def test_settlements_table_schema(self):
        table = Base.metadata.tables["settlements"]
        expected_cols = ["id", "name", "location", "population", "state", "district"]
        for col in expected_cols:
            assert col in table.c

    def test_affected_settlements_table_schema_and_constraints(self):
        table = Base.metadata.tables["affected_settlements"]
        expected_cols = [
            "id",
            "simulation_run_id",
            "settlement_id",
            "arrival_time_minutes",
            "estimated_depth_m",
        ]
        for col in expected_cols:
            assert col in table.c

        constraint_names = {c.name for c in table.constraints if hasattr(c, "name")}
        assert "uq_run_settlement" in constraint_names
        assert "chk_arrival_nonnegative" in constraint_names

    def test_case_studies_table_schema(self):
        table = Base.metadata.tables["case_studies"]
        expected_cols = [
            "id",
            "scenario_id",
            "simulation_run_id",
            "event_year",
            "description",
            "source_reference",
            "created_at",
        ]
        for col in expected_cols:
            assert col in table.c

    def test_exports_table_schema(self):
        table = Base.metadata.tables["exports"]
        expected_cols = ["id", "simulation_run_id", "user_id", "file_url", "format", "created_at"]
        for col in expected_cols:
            assert col in table.c

    def test_enum_definitions(self):
        assert list(UserRole) == [UserRole.ANALYST]
        assert set(BreachType) == {BreachType.STRUCTURAL, BreachType.LANDSLIDE_GLOF}
        assert set(RunStatus) == {
            RunStatus.PENDING,
            RunStatus.RUNNING,
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
        }
        assert set(PipelineStage) == {
            PipelineStage.DEM_FETCH,
            PipelineStage.BREACH_ESTIMATION,
            PipelineStage.FLOOD_ROUTING,
            PipelineStage.SUMMARY_GENERATION,
        }
        assert set(ExportFormat) == {ExportFormat.PDF, ExportFormat.JSON}


class TestAlembicMigrationsReversibility:
    """Test that Alembic migrations generate clean, reversible SQL."""

    @pytest.fixture
    def alembic_cfg(self):
        ini_path = os.path.join(BASE_DIR, "alembic.ini")
        cfg = Config(ini_path)
        return cfg

    def test_migration_upgrade_sql_generation(self, alembic_cfg, capsys):
        """Verify that upgrade --sql produces DDL for all 8 tables and PostGIS."""
        command.upgrade(alembic_cfg, "head", sql=True)
        captured = capsys.readouterr()
        sql = captured.out

        assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
        assert "CREATE TABLE users" in sql
        assert "CREATE TABLE scenarios" in sql
        assert "CREATE TABLE simulation_runs" in sql
        assert "CREATE TABLE flood_results" in sql
        assert "CREATE TABLE settlements" in sql
        assert "CREATE TABLE affected_settlements" in sql
        assert "CREATE TABLE case_studies" in sql
        assert "CREATE TABLE exports" in sql

    def test_migration_downgrade_sql_generation(self, alembic_cfg, capsys):
        """Verify that downgrade --sql produces clean drops in reverse order."""
        command.downgrade(alembic_cfg, "001_initial_schema:base", sql=True)
        captured = capsys.readouterr()
        sql = captured.out

        assert "DROP TABLE exports" in sql
        assert "DROP TABLE case_studies" in sql
        assert "DROP TABLE affected_settlements" in sql
        assert "DROP TABLE settlements" in sql
        assert "DROP TABLE flood_results" in sql
        assert "DROP TABLE simulation_runs" in sql
        assert "DROP TABLE scenarios" in sql
        assert "DROP TABLE users" in sql
        assert "DROP TYPE IF EXISTS user_role" in sql


class TestSeedDataIntegrity:
    """Verify seed data creation, relationships, and queries using SQLite in-memory mock."""

    @pytest.fixture
    def mock_db_session(self):
        # Configure GeoAlchemy2 for in-memory SQLite testing without SpatiaLite
        import geoalchemy2.admin.dialects.sqlite as sqlite_admin
        from geoalchemy2 import Geometry
        from geoalchemy2.elements import WKTElement
        from sqlalchemy.ext.compiler import compiles

        sqlite_admin.after_create = lambda *a, **k: None
        sqlite_admin.before_create = lambda *a, **k: None

        @compiles(Geometry, "sqlite")
        def compile_geom(el, comp, **kw):
            return "TEXT"

        @compiles(WKTElement, "sqlite")
        def compile_wkt(el, comp, **kw):
            return comp.process(el.data, **kw) if hasattr(el, "data") else str(el)

        from sqlalchemy.dialects.postgresql import UUID as PG_UUID

        @compiles(PG_UUID, "sqlite")
        def compile_uuid(type_, comp, **kw):
            return "TEXT"

        orig_bind = Geometry.bind_expression
        orig_col = Geometry.column_expression
        orig_res = Geometry.result_processor

        Geometry.bind_expression = lambda self, bindvalue: (
            bindvalue.data if hasattr(bindvalue, "data") else bindvalue
        )
        Geometry.column_expression = lambda self, col: col
        Geometry.result_processor = lambda self, dialect, coltype: lambda value: value

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            Geometry.bind_expression = orig_bind
            Geometry.column_expression = orig_col
            Geometry.result_processor = orig_res

    def test_system_user_seeding(self, mock_db_session):
        users = seed_users(mock_db_session)
        assert "system@floodpath.internal" in users
        assert "analyst@floodpath.internal" in users

        system_user = users["system@floodpath.internal"]
        assert system_user.id == SYSTEM_USER_ID
        assert system_user.role == UserRole.ANALYST
        # Verify password verifies against bcrypt
        assert bcrypt.checkpw(b"FloodPath2026!", system_user.password_hash.encode("utf-8"))

        analyst_user = users["analyst@floodpath.internal"]
        assert analyst_user.id == ANALYST_USER_ID
        assert analyst_user.role == UserRole.ANALYST

    def test_settlements_seeding(self, mock_db_session):
        settlements = seed_settlements(mock_db_session)
        assert len(settlements) >= 10
        assert "Rini Village" in settlements
        assert "Tapovan" in settlements
        assert "Joshimath" in settlements
        assert "Chamoli" in settlements

        rini = settlements["Rini Village"]
        assert rini.population == 420
        assert rini.district == "Chamoli"
        assert rini.state == "Uttarakhand"

    def test_case_study_and_simulation_run_integrity(self, mock_db_session):
        case_study = seed_case_studies(mock_db_session)
        assert case_study.event_year == 2021
        assert "Rishi Ganga" in case_study.description

        # Verify scenario exists and is owned by system user
        scenario = mock_db_session.execute(
            select(Scenario).where(Scenario.id == case_study.scenario_id)
        ).scalar_one()
        assert scenario.user_id == SYSTEM_USER_ID
        assert scenario.dam_height_m == 36.00
        assert scenario.dam_volume_m3 == 27000000.00
        assert scenario.breach_type == BreachType.LANDSLIDE_GLOF

        # Verify simulation run exists and succeeded
        run = mock_db_session.execute(
            select(SimulationRun).where(SimulationRun.id == case_study.simulation_run_id)
        ).scalar_one()
        assert run.status == RunStatus.SUCCEEDED
        assert run.scenario_id == scenario.id

        # Verify non-empty flood results
        flood_results = (
            mock_db_session.execute(
                select(FloodResult).where(FloodResult.simulation_run_id == run.id)
            )
            .scalars()
            .all()
        )
        assert len(flood_results) >= 8
        time_steps = [fr.time_step_minutes for fr in flood_results]
        assert 0 in time_steps
        assert 15 in time_steps
        assert 30 in time_steps
        assert 45 in time_steps

        # Verify non-empty affected settlements
        affected = (
            mock_db_session.execute(
                select(AffectedSettlement).where(AffectedSettlement.simulation_run_id == run.id)
            )
            .scalars()
            .all()
        )
        assert len(affected) >= 7

        # Verify arrival order: Rini (18m) < Tapovan (42m) < Joshimath (72m)
        aff_by_time = sorted(affected, key=lambda a: a.arrival_time_minutes)
        assert aff_by_time[0].arrival_time_minutes == 18
        assert aff_by_time[1].arrival_time_minutes == 42
