"""Module 5: Database persistence layer"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Literal, Dict, Any, Tuple

from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    text,
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
    _ensure_linear_walls_schema(engine)


def _ensure_linear_walls_schema(engine) -> None:
    """
    Add newly introduced nullable columns for existing SQLite databases.
    This keeps backward compatibility without a migration tool.
    """
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(linear_walls)").all()
        if not rows:
            return
        existing_cols = {row[1] for row in rows}
        if "level_from" not in existing_cols:
            conn.exec_driver_sql("ALTER TABLE linear_walls ADD COLUMN level_from TEXT")
        if "level_to" not in existing_cols:
            conn.exec_driver_sql("ALTER TABLE linear_walls ADD COLUMN level_to TEXT")


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
    linear_walls: Mapped[List["LinearWall"]] = relationship(back_populates="project", cascade="all, delete-orphan")
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


class LinearWall(Base):
    __tablename__ = "linear_walls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grid_line: Mapped[str] = mapped_column(String(50), nullable=False)
    from_grid: Mapped[str] = mapped_column(String(50), nullable=False)
    to_grid: Mapped[str] = mapped_column(String(50), nullable=False)
    length_mm: Mapped[float] = mapped_column(Float, nullable=False)
    level_from: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    level_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    height_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default=text("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="linear_walls")


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

    @staticmethod
    def _normalize_optional_level_name(value: Any) -> Optional[str]:
        """Normalize optional level names; blank values are treated as missing."""
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _coerce_linear_wall_height_mm(value: Any) -> float:
        """
        Keep linear wall cached height resilient for legacy rows.
        Height is derived at runtime; persisted value is optional cache.
        """
        if value in (None, ""):
            return 0.0
        return float(value)

    def get_or_create_project(self, project_name: str, dim_format: DimFormat) -> int:
        """
        Get an existing project ID by name, or create a new project with the
        given dim_format and internal_unit='mm'.

        IMPORTANT:
        - For existing projects this does NOT change dim_format anymore.
          Use update_project_dim_format(...) when the user explicitly chooses
          a new default display/input format.
        """
        with self.Session() as s:
            p = s.query(Project).filter(Project.name == project_name).one_or_none()
            if p is None:
                p = Project(name=project_name, dim_format=dim_format, internal_unit="mm")
                s.add(p)
                s.commit()
                return p.id

            return p.id

    def update_project_dim_format(self, project_id: int, dim_format: DimFormat) -> None:
        """Explicitly update a project's default display/input dim_format."""
        with self.Session() as s:
            p = s.query(Project).filter(Project.id == project_id).one_or_none()
            if p is None:
                raise ValueError(f"Project not found for id={project_id}")
            p.dim_format = dim_format
            p.updated_at = datetime.utcnow()
            s.commit()

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

    # ---------------------------
    # PROJECT CRUD (by name)
    # ---------------------------

    def _project_id_by_name(self, session, project_name: str) -> Optional[int]:
        p = session.query(Project).filter(Project.name == project_name).one_or_none()
        return p.id if p else None

    def list_projects(self) -> List[Dict[str, Any]]:
        """Returns list of dicts: name, created_at, updated_at, shafts_count, levels_count."""
        with self.Session() as s:
            projects = s.query(Project).order_by(Project.updated_at.desc()).all()
            out = []
            for p in projects:
                shafts_count = s.query(ShaftPlan).filter(ShaftPlan.project_id == p.id).count()
                levels_count = s.query(Level).filter(Level.project_id == p.id).count()
                out.append({
                    "name": p.name,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "shafts_count": shafts_count,
                    "levels_count": levels_count,
                })
            return out

    def get_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Returns metadata + dim_format for the project, or None if not found."""
        with self.Session() as s:
            p = s.query(Project).filter(Project.name == project_name).one_or_none()
            if p is None:
                return None
            return {
                "id": p.id,
                "name": p.name,
                "dim_format": p.dim_format,
                "internal_unit": p.internal_unit,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }

    def rename_project(self, old_name: str, new_name: str) -> None:
        with self.Session() as s:
            p = s.query(Project).filter(Project.name == old_name).one_or_none()
            if p is None:
                raise ValueError(f"Project not found: {old_name}")
            existing = s.query(Project).filter(Project.name == new_name).one_or_none()
            if existing is not None:
                raise ValueError(f"Project already exists: {new_name}")
            p.name = new_name
            p.updated_at = datetime.now(timezone.utc)
            s.commit()

    def delete_project(self, project_name: str) -> None:
        with self.Session() as s:
            p = s.query(Project).filter(Project.name == project_name).one_or_none()
            if p is None:
                raise ValueError(f"Project not found: {project_name}")
            s.delete(p)
            s.commit()

    # ---------------------------
    # SHAFT CRUD (by project_name)
    # ---------------------------

    def list_shafts(self, project_name: str) -> List[Dict[str, Any]]:
        """Returns list of shaft dicts (name, grid_*, width_mm, height_mm) for the project."""
        with self.Session() as s:
            pid = self._project_id_by_name(s, project_name)
            if pid is None:
                return []
            rows = (
                s.query(ShaftPlan)
                .filter(ShaftPlan.project_id == pid)
                .order_by(ShaftPlan.id.asc())
                .all()
            )
            return [
                {
                    "name": r.name,
                    "grid_left": r.grid_left,
                    "grid_right": r.grid_right,
                    "grid_bottom": r.grid_bottom,
                    "grid_top": r.grid_top,
                    "width_mm": float(r.width_mm),
                    "height_mm": float(r.height_mm),
                }
                for r in rows
            ]

    def get_shaft(self, project_name: str, shaft_name: str) -> Optional[Dict[str, Any]]:
        with self.Session() as s:
            pid = self._project_id_by_name(s, project_name)
            if pid is None:
                return None
            r = (
                s.query(ShaftPlan)
                .filter(ShaftPlan.project_id == pid, ShaftPlan.name == shaft_name)
                .one_or_none()
            )
            if r is None:
                return None
            return {
                "name": r.name,
                "grid_left": r.grid_left,
                "grid_right": r.grid_right,
                "grid_bottom": r.grid_bottom,
                "grid_top": r.grid_top,
                "width_mm": float(r.width_mm),
                "height_mm": float(r.height_mm),
            }

    def upsert_shaft(self, project_name: str, shaft_dict: Dict[str, Any]) -> None:
        """Insert if missing, update if exists (by project + shaft name)."""
        with self.Session() as s:
            pid = self._project_id_by_name(s, project_name)
            if pid is None:
                raise ValueError(f"Project not found: {project_name}")
            name = shaft_dict.get("name")
            if not name:
                raise ValueError("shaft_dict must contain 'name'")
            existing = (
                s.query(ShaftPlan)
                .filter(ShaftPlan.project_id == pid, ShaftPlan.name == name)
                .one_or_none()
            )
            payload = {
                "name": shaft_dict["name"],
                "grid_left": shaft_dict["grid_left"],
                "grid_right": shaft_dict["grid_right"],
                "grid_bottom": shaft_dict["grid_bottom"],
                "grid_top": shaft_dict["grid_top"],
                "width_mm": float(shaft_dict["width_mm"]),
                "height_mm": float(shaft_dict["height_mm"]),
            }
            if existing is not None:
                for k, v in payload.items():
                    setattr(existing, k, v)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                s.add(ShaftPlan(project_id=pid, **payload))
            p = s.query(Project).filter(Project.id == pid).one()
            p.updated_at = datetime.now(timezone.utc)
            s.commit()

    def delete_shaft(self, project_name: str, shaft_name: str) -> None:
        with self.Session() as s:
            pid = self._project_id_by_name(s, project_name)
            if pid is None:
                raise ValueError(f"Project not found: {project_name}")
            r = (
                s.query(ShaftPlan)
                .filter(ShaftPlan.project_id == pid, ShaftPlan.name == shaft_name)
                .one_or_none()
            )
            if r is None:
                raise ValueError(f"Shaft not found: {project_name} / {shaft_name}")
            s.delete(r)
            p = s.query(Project).filter(Project.id == pid).one()
            p.updated_at = datetime.now(timezone.utc)
            s.commit()

    # ---------------------------
    # LEVELS CRUD (by project_name)
    # ---------------------------

    def get_levels(self, project_name: str) -> Tuple[List[str], List[float]]:
        """Returns (levels[], deltas_mm[]) for the project. Empty if no levels."""
        proj = self.get_project(project_name)
        if proj is None:
            return [], []
        levels_rows, step_rows = self.load_levels_and_steps(proj["id"])
        levels = [lv.name for lv in sorted(levels_rows, key=lambda x: x.order_index)]
        if len(levels) < 2:
            return levels, []
        step_map = {(st.from_level_id, st.to_level_id): float(st.delta_mm) for st in step_rows}
        level_ids = [lv.id for lv in sorted(levels_rows, key=lambda x: x.order_index)]
        deltas = []
        for i in range(len(level_ids) - 1):
            key = (level_ids[i], level_ids[i + 1])
            deltas.append(step_map.get(key, 0.0))
        return levels, deltas

    def save_levels(self, project_name: str, levels: List[str], deltas_mm: List[float]) -> None:
        """Replaces existing levels and steps for the project."""
        if len(levels) < 2:
            raise ValueError("Need at least 2 levels.")
        if len(deltas_mm) != len(levels) - 1:
            raise ValueError("deltas_mm must have length N-1 for N levels.")
        proj = self.get_project(project_name)
        if proj is None:
            raise ValueError(f"Project not found: {project_name}")
        self.replace_levels_and_steps(
            proj["id"],
            level_names_in_order=levels,
            deltas_mm_between_consecutive=deltas_mm,
        )

    # ---------------------------
    # LINEAR WALLS CRUD (by project_id)
    # ---------------------------

    def get_linear_walls(self, project_id: int) -> List[Dict[str, Any]]:
        """Return linear walls for a project as list of dicts."""
        with self.Session() as s:
            rows = (
                s.query(LinearWall)
                .filter(LinearWall.project_id == project_id)
                .order_by(LinearWall.id.asc())
                .all()
            )
            walls: List[Dict[str, Any]] = []
            for r in rows:
                walls.append(
                    {
                        "id": r.id,
                        "project_id": r.project_id,
                        "name": r.name,
                        "grid_line": r.grid_line,
                        "from_grid": r.from_grid,
                        "to_grid": r.to_grid,
                        "length_mm": float(r.length_mm),
                        "level_from": self._normalize_optional_level_name(r.level_from),
                        "level_to": self._normalize_optional_level_name(r.level_to),
                        "height_mm": self._coerce_linear_wall_height_mm(r.height_mm),
                        "notes": r.notes,
                    }
                )
            return walls

    def add_linear_wall(self, project_id: int, payload: Dict[str, Any]) -> int:
        """Create a new linear wall for a project. Returns new wall id."""
        with self.Session() as s:
            proj = s.query(Project).filter(Project.id == project_id).one_or_none()
            if proj is None:
                raise ValueError(f"Project not found for id={project_id}")

            wall = LinearWall(
                project_id=project_id,
                name=payload["name"],
                grid_line=payload["grid_line"],
                from_grid=payload["from_grid"],
                to_grid=payload["to_grid"],
                length_mm=float(payload["length_mm"]),
                level_from=self._normalize_optional_level_name(payload.get("level_from")),
                level_to=self._normalize_optional_level_name(payload.get("level_to")),
                height_mm=self._coerce_linear_wall_height_mm(payload.get("height_mm")),
                notes=payload.get("notes"),
            )
            s.add(wall)
            proj.updated_at = datetime.utcnow()
            s.commit()
            return wall.id

    def update_linear_wall(self, wall_id: int, payload: Dict[str, Any]) -> None:
        """Update an existing linear wall by id."""
        with self.Session() as s:
            wall = s.query(LinearWall).filter(LinearWall.id == wall_id).one_or_none()
            if wall is None:
                raise ValueError(f"Linear wall not found for id={wall_id}")

            for field in (
                "name",
                "grid_line",
                "from_grid",
                "to_grid",
                "length_mm",
                "level_from",
                "level_to",
                "height_mm",
                "notes",
            ):
                if field in payload:
                    value = payload[field]
                    if field == "length_mm" and value is not None:
                        value = float(value)
                    if field in ("level_from", "level_to"):
                        value = self._normalize_optional_level_name(value)
                    if field == "height_mm":
                        value = self._coerce_linear_wall_height_mm(value)
                    setattr(wall, field, value)

            wall.updated_at = datetime.utcnow()
            proj = s.query(Project).filter(Project.id == wall.project_id).one()
            proj.updated_at = datetime.utcnow()
            s.commit()

    def delete_linear_wall(self, wall_id: int) -> None:
        """Delete a linear wall by id."""
        with self.Session() as s:
            wall = s.query(LinearWall).filter(LinearWall.id == wall_id).one_or_none()
            if wall is None:
                raise ValueError(f"Linear wall not found for id={wall_id}")
            proj = s.query(Project).filter(Project.id == wall.project_id).one()
            s.delete(wall)
            proj.updated_at = datetime.utcnow()
            s.commit()
