"""Module 5: Database persistence layer"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Literal, Dict, Any

from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON


# ---------------------------
# DATABASE SETUP
# ---------------------------

class Base(DeclarativeBase):
    pass


def build_db_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def init_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(build_db_url(db_path), echo=False, future=True)
    return engine


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# ---------------------------
# CORE ENTITIES
# ---------------------------

DimFormat = Literal["MM_DECIMAL_2", "FT_DECIMAL_2", "FT_IN_FRAC_QUARTER"]


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    dim_format: Mapped[str] = mapped_column(String(50), nullable=False, default="MM_DECIMAL_2")
    internal_unit: Mapped[str] = mapped_column(String(10), nullable=False, default="mm")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    shafts: Mapped[List["ShaftPlan"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    levels: Mapped[List["Level"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    level_steps: Mapped[List["LevelStep"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[List["Run"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    exports: Mapped[List["ExportRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ShaftPlan(Base):
    __tablename__ = "shafts"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_shaft_name_per_project"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grid_left: Mapped[str] = mapped_column(String(50), nullable=False)
    grid_right: Mapped[str] = mapped_column(String(50), nullable=False)
    grid_bottom: Mapped[str] = mapped_column(String(50), nullable=False)
    grid_top: Mapped[str] = mapped_column(String(50), nullable=False)
    width_mm: Mapped[float] = mapped_column(Float, nullable=False)
    height_mm: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="shafts")


class Level(Base):
    __tablename__ = "levels"
    __table_args__ = (UniqueConstraint("project_id", "order_index", name="uq_level_order_per_project"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="levels")


class LevelStep(Base):
    __tablename__ = "level_steps"
    __table_args__ = (UniqueConstraint("project_id", "from_level_id", "to_level_id", name="uq_step_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    from_level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False)
    to_level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False)
    delta_mm: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="level_steps")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="started")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dxf_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="runs")


class ExportRecord(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(SQLITE_JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="exports")


# ---------------------------
# REPOSITORY / MODULE 5 API
# ---------------------------

@dataclass(frozen=True)
class DBConfig:
    db_path: Path


class DB:
    """Thin wrapper for database operations"""

    def __init__(self, cfg: DBConfig):
        self.engine = init_engine(cfg.db_path)
        init_db(self.engine)
        self.Session = make_session_factory(self.engine)

    def get_or_create_project(self, project_name: str, dim_format: DimFormat) -> int:
        with self.Session() as s:
            p = s.query(Project).filter(Project.name == project_name).one_or_none()
            if p is None:
                p = Project(name=project_name, dim_format=dim_format, internal_unit="mm")
                s.add(p)
                s.commit()
                return p.id

            p.dim_format = dim_format
            p.updated_at = datetime.utcnow()
            s.commit()
            return p.id

    def replace_shafts(self, project_id: int, shafts: List[Dict[str, Any]]) -> None:
        with self.Session() as s:
            s.query(ShaftPlan).filter(ShaftPlan.project_id == project_id).delete()
            for sh in shafts:
                s.add(ShaftPlan(project_id=project_id, **sh))
            p = s.query(Project).filter(Project.id == project_id).one()
            p.updated_at = datetime.utcnow()
            s.commit()

    def load_shafts(self, project_id: int) -> List[ShaftPlan]:
        with self.Session() as s:
            return (
                s.query(ShaftPlan)
                .filter(ShaftPlan.project_id == project_id)
                .order_by(ShaftPlan.id.asc())
                .all()
            )

    def replace_levels_and_steps(
        self,
        project_id: int,
        level_names_in_order: List[str],
        deltas_mm_between_consecutive: List[float],
    ) -> None:
        if len(level_names_in_order) < 2:
            raise ValueError("Need at least 2 levels.")
        if len(deltas_mm_between_consecutive) != len(level_names_in_order) - 1:
            raise ValueError("deltas must be N-1 between consecutive levels.")

        with self.Session() as s:
            s.query(LevelStep).filter(LevelStep.project_id == project_id).delete()
            s.query(Level).filter(Level.project_id == project_id).delete()

            levels: List[Level] = []
            for idx, nm in enumerate(level_names_in_order):
                lv = Level(project_id=project_id, name=nm, order_index=idx)
                s.add(lv)
                levels.append(lv)
            s.flush()

            for i, delta in enumerate(deltas_mm_between_consecutive):
                s.add(
                    LevelStep(
                        project_id=project_id,
                        from_level_id=levels[i].id,
                        to_level_id=levels[i + 1].id,
                        delta_mm=float(delta),
                    )
                )

            p = s.query(Project).filter(Project.id == project_id).one()
            p.updated_at = datetime.utcnow()
            s.commit()

    def load_levels_and_steps(self, project_id: int):
        with self.Session() as s:
            levels = (
                s.query(Level)
                .filter(Level.project_id == project_id)
                .order_by(Level.order_index.asc())
                .all()
            )
            steps = s.query(LevelStep).filter(LevelStep.project_id == project_id).all()
            return levels, steps

    def start_run(self, project_id: int) -> int:
        with self.Session() as s:
            r = Run(project_id=project_id, status="started")
            s.add(r)
            s.commit()
            return r.id

    def finish_run_ok(self, run_id: int, dxf_path: Optional[str], pdf_path: Optional[str]) -> None:
        with self.Session() as s:
            r = s.query(Run).filter(Run.id == run_id).one()
            r.status = "ok"
            r.finished_at = datetime.utcnow()
            r.dxf_path = dxf_path
            r.pdf_path = pdf_path
            s.commit()

    def finish_run_error(self, run_id: int, notes: str) -> None:
        with self.Session() as s:
            r = s.query(Run).filter(Run.id == run_id).one()
            r.status = "error"
            r.finished_at = datetime.utcnow()
            r.notes = notes
            s.commit()

    def add_export_record(self, project_id: int, export_type: str, file_path: str, meta: dict) -> int:
        with self.Session() as s:
            e = ExportRecord(project_id=project_id, export_type=export_type, file_path=file_path, meta=meta)
            s.add(e)
            s.commit()
            return e.id
