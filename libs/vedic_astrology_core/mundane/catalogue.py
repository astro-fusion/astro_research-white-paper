"""Method catalogue of the retrospective mundane chart engine (ADR-006, section 4).

One YAML file per method in ``rules/mundane/methods/``. A method is a way to
compute something (navamsa, Vimshottari, a transit counted from the natal
Moon). The engine refuses to compute a method that has no catalogue entry, a
method with no cited definition, or a method below the level a use requires.

``citation_status`` and ``level`` are computed here from the entry's own
fields and fixtures. A file that writes either of them fails to load.

File names start with an underscore (``_varga.d9.yaml``) because the rule
loader (``rules.loader.discover``) walks all of ``rules/`` and skips files
whose name starts with ``_``. Without the prefix every method file would be
read, and rejected, as a rule.
"""

import hashlib
import importlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Family = Literal["varga", "dasha", "transit", "sky", "annual", "house", "cycle"]
Tradition = Literal["samhita", "jataka_applied", "practitioner", "western_mundane"]
Tier = Literal["core", "extended", "phase2", "phase3"]
Scope = Literal["case_file", "aggregate"]
CitationStatus = Literal["unverified", "page_cited", "verified"]
Use = Literal["case_file", "explore", "confirmatory"]

#: Status to ADR-004 level (a page-cited entry with a reference case is L2).
STATUS_LEVEL = {"unverified": 0, "page_cited": 1, "verified": 3}
#: Minimum number of reference cases for ``verified`` (ADR-006 section 4.2).
MIN_VERIFIED_CASES = 3
#: Lowest status each use accepts (ADR-006 section 4.2 table).
USE_MIN_STATUS = {"case_file": "unverified", "explore": "page_cited", "confirmatory": "verified"}
_RANK = {"unverified": 0, "page_cited": 1, "verified": 2}

_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
_COMPUTED = ("citation_status", "level")


class CatalogueError(ValueError):
    """A method file is invalid, or a method may not be used."""


class MethodNotCited(CatalogueError):
    """The method has no cited definition or implementation to compute."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Name(_Strict):
    sanskrit: Optional[str] = None
    english: str


class Source(_Strict):
    text: Optional[str] = None
    edition: Optional[str] = None
    translator: Optional[str] = None
    chapter: Optional[str] = None
    verse: Optional[str] = None
    quote: Optional[str] = None
    url: Optional[str] = None
    archive_url: Optional[str] = None
    checked_by: Optional[str] = None
    checked_at: Optional[str] = None


class Definition(_Strict):
    inputs: List[str] = Field(default_factory=list)
    formula: Optional[str] = None
    conventions: Dict[str, Any] = Field(default_factory=dict)
    variants: List[Dict[str, Any]] = Field(default_factory=list)


class Implementation(_Strict):
    module: str
    function: str


class Needs(_Strict):
    founding_time_precision_minutes: Optional[float] = None
    place: bool = False


class Method(_Strict):
    id: str
    name: Name
    family: Family
    tradition: Tradition
    tier: Tier
    source: Source
    definition: Definition
    implementation: Optional[Implementation] = None
    predicates: List[str] = Field(default_factory=list)
    needs: Needs
    change_period: str
    reference_cases: List[str] = Field(default_factory=list)
    scope: List[Scope]
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check(self) -> "Method":
        if not _ID.match(self.id):
            raise ValueError(f"id {self.id!r} must look like family.name")
        if self.id.split(".")[0] != self.family:
            raise ValueError(f"id {self.id!r} must start with its family {self.family!r}")
        if self.tier == "core" and not (self.definition.formula or "").strip():
            raise ValueError("a core method needs definition.formula")
        if self.tier == "extended" and "aggregate" in self.scope:
            raise ValueError("an extended method may not enter the aggregate report")
        if not self.scope:
            raise ValueError("scope may not be empty")
        return self

    # ---- computed, never written in the file -------------------------------
    @property
    def source_is_cited(self) -> bool:
        s = self.source
        has_place = bool((s.chapter or "").strip() or (s.verse or "").strip())
        return all(
            [(s.text or "").strip(), (s.edition or "").strip(), has_place,
             (s.quote or "").strip(), (s.checked_by or "").strip(),
             (s.checked_at or "").strip()]
        )

    def existing_reference_cases(self, root: Optional[Path] = None) -> List[str]:
        base = root or repo_root()
        return [r for r in self.reference_cases if (base / r).is_file()]

    def citation_status(self, root: Optional[Path] = None) -> CitationStatus:
        if not self.source_is_cited or not self.definition.formula:
            return "unverified"
        if len(self.existing_reference_cases(root)) >= MIN_VERIFIED_CASES:
            return "verified"
        return "page_cited"

    def level(self, root: Optional[Path] = None) -> int:
        status = self.citation_status(root)
        if status == "page_cited" and self.existing_reference_cases(root):
            return 2
        return STATUS_LEVEL[status]

    def allowed_in(self, use: Use, root: Optional[Path] = None) -> bool:
        """Whether the method's status is enough for ``use`` (section 4.2)."""
        if use != "case_file" and self.tier != "core":
            return False
        return _RANK[self.citation_status(root)] >= _RANK[USE_MIN_STATUS[use]]

    def resolve(self) -> Callable:
        """The implementing callable; raises ``MethodNotCited`` if there is none."""
        if self.implementation is None:
            raise MethodNotCited(
                f"method {self.id!r} is not cited: no implementation until a text, "
                "edition and page define it (owner task H11)"
            )
        return _import(self.implementation)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_methods_dir() -> Path:
    return repo_root() / "rules" / "mundane" / "methods"


def _import(impl: Implementation) -> Callable:
    try:
        module = importlib.import_module(impl.module)
    except ImportError as exc:
        raise CatalogueError(f"implementation module {impl.module!r} does not import: {exc}")
    func = getattr(module, impl.function, None)
    if not callable(func):
        raise CatalogueError(f"{impl.module}.{impl.function} does not exist")
    return func


class Catalogue:
    """All methods, by id, with a stable content hash."""

    def __init__(self, methods: Dict[str, Method], raw: Dict[str, Dict[str, Any]], root: Path):
        self.methods = methods
        self._raw = raw
        self.root = root

    def __contains__(self, method_id: str) -> bool:
        return method_id in self.methods

    def __iter__(self):
        return iter(self.methods.values())

    def __len__(self) -> int:
        return len(self.methods)

    def get(self, method_id: str) -> Method:
        """The entry for ``method_id``; an unknown id is refused."""
        try:
            return self.methods[method_id]
        except KeyError:
            raise CatalogueError(f"method {method_id!r} has no catalogue entry") from None

    def compute(self, method_id: str, *args: Any, **kwargs: Any) -> Any:
        """Run a method's implementation. Refuses unknown and uncited methods."""
        return self.get(method_id).resolve()(*args, **kwargs)

    def require(self, method_id: str, use: Use) -> Method:
        """Return the method if its status allows ``use``, else raise."""
        method = self.get(method_id)
        if not method.allowed_in(use, self.root):
            raise CatalogueError(
                f"method {method_id!r} is {method.citation_status(self.root)} "
                f"(tier {method.tier}) and may not be used for {use}"
            )
        return method

    def hash(self) -> str:
        """SHA-256 of the entries' content, independent of file order and layout."""
        blob = json.dumps(self._raw, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _format_errors(path: Path, exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        where = ".".join(str(p) for p in err["loc"]) or "<file>"
        msg = err["msg"].removeprefix("Value error, ")
        if err["type"] == "extra_forbidden" and err["loc"][-1] in _COMPUTED:
            msg = f"'{err['loc'][-1]}' is computed from the entry and may not be written"
        elif err["type"] == "extra_forbidden":
            msg = "unknown field"
        lines.append(f"{path.name}: {where}: {msg}")
    return "\n".join(lines)


def load_method_file(path: Path) -> Tuple[Method, Dict[str, Any]]:
    """Parse and validate one method file."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CatalogueError(f"{path.name}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogueError(f"{path.name}: expected a mapping")
    try:
        method = Method.model_validate(data)
    except ValidationError as exc:
        raise CatalogueError(_format_errors(path, exc)) from exc
    stem = path.stem.lstrip("_")
    if stem != method.id:
        raise CatalogueError(f"{path.name}: file name must be '_{method.id}.yaml'")
    for name in method.predicates:
        _check_predicate(path, name)
    if method.implementation is not None:
        _import(method.implementation)
    return method, data


def _check_predicate(path: Path, name: str) -> None:
    from vedic_astrology_core.rules.predicates import PREDICATES

    if name not in PREDICATES:
        raise CatalogueError(f"{path.name}: predicate {name!r} is not registered")


def load_catalogue(directory: Optional[Path] = None, root: Optional[Path] = None) -> Catalogue:
    """Load every ``*.yaml`` in the methods directory. Duplicate ids fail."""
    folder = Path(directory) if directory else default_methods_dir()
    methods: Dict[str, Method] = {}
    raw: Dict[str, Dict[str, Any]] = {}
    for path in sorted(folder.glob("*.yaml")):
        method, data = load_method_file(path)
        if method.id in methods:
            raise CatalogueError(f"{path.name}: duplicate method id {method.id!r}")
        methods[method.id] = method
        raw[method.id] = data
    return Catalogue(methods, raw, Path(root) if root else repo_root())
