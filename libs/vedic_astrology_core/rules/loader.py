"""Load ``rules/**/*.yaml``, validate them, and index them in a registry.

Errors are collected, not raised one at a time, and each names the file,
the line when the YAML parser knows it, the field path, and what to do.
"""

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

import yaml
from pydantic import ValidationError

from .engine import rule_inputs
from .predicates import PREDICATES
from .schema import Rule, suggest

PathLike = Union[str, Path]


@dataclass(frozen=True)
class RuleProblem:
    """One validation problem in one file."""

    path: str
    message: str
    field: str = ""
    line: Optional[int] = None

    def __str__(self) -> str:
        """``file:line: field: message``."""
        where = self.path + (f":{self.line}" if self.line else "")
        return f"{where}: {self.field + ': ' if self.field else ''}{self.message}"


@dataclass(frozen=True)
class LoadedRule:
    """A validated rule and the file it came from."""

    rule: Rule
    path: Path


class RuleLoadError(ValueError):
    """Raised by :meth:`RuleRegistry.load` when any rule file is invalid."""

    def __init__(self, problems: List[RuleProblem]):
        """Keep the problems; the message lists them."""
        self.problems = problems
        super().__init__("\n".join(str(p) for p in problems))


def default_rules_dir() -> Path:
    """``$ASTRO_RULES_DIR``, else the repository's ``rules/``, else ``./rules``."""
    env = os.environ.get("ASTRO_RULES_DIR")
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[3] / "rules"
    if repo.is_dir():
        return repo
    return Path.cwd() / "rules"


def discover(paths: Optional[Sequence[PathLike]] = None) -> List[Path]:
    """Rule files under ``paths`` (directories are searched recursively).

    Files whose name starts with ``_`` (shared tables) are skipped.
    """
    targets = [Path(p) for p in (paths or [default_rules_dir()])]
    files: List[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(
                p
                for p in sorted(target.rglob("*.y*ml"))
                if not p.name.startswith("_") and p.suffix in (".yaml", ".yml")
            )
        else:
            files.append(target)
    return files


# ------------------------------------------------------------ line numbers
def _line_of(node: Any, loc: Tuple) -> Optional[int]:
    """Best line for a Pydantic error location in a composed YAML node."""
    line = node.start_mark.line + 1 if node is not None else None
    for key in loc:
        if isinstance(node, yaml.MappingNode):
            nxt = None
            for k, v in node.value:
                if k.value == key:
                    nxt = v
                    line = k.start_mark.line + 1
                    break
            if nxt is None:
                continue  # a union tag, not a YAML key
            node = nxt
        elif isinstance(node, yaml.SequenceNode) and isinstance(key, int):
            if key < len(node.value):
                node = node.value[key]
                line = node.start_mark.line + 1
    return line


def _field_path(loc: Tuple) -> str:
    parts: List[str] = []
    for key in loc:
        if isinstance(key, int):
            parts.append(f"[{key}]")
        elif parts and parts[-1].lstrip(".") == key:
            continue  # tagged-union duplicate (in_sign.in_sign)
        elif key in ("all", "any") and parts and parts[-1].lstrip(".") == key:
            continue
        else:
            parts.append(("." if parts else "") + str(key))
    return "".join(parts)


def _message(err: Dict[str, Any]) -> str:
    msg = err["msg"]
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, ") :]
    if err["type"] == "extra_forbidden":
        key = err["loc"][-1]
        allowed = _allowed_keys(err["loc"][:-1])
        msg = f"unknown field '{key}'." + (
            suggest(key, allowed) + f" Allowed: {', '.join(allowed)}" if allowed else ""
        )
    elif err["type"] == "missing":
        msg = f"required field '{err['loc'][-1]}' is missing"
    elif err["type"] == "timezone_aware":
        msg = "the moment needs a time zone, e.g. 2024-05-03T06:00:00+05:45 or ...Z"
    return msg


def _allowed_keys(loc: Tuple) -> List[str]:
    for key in reversed(loc):
        if isinstance(key, str) and key in PREDICATES:
            model = PREDICATES[key].params
            return [i.alias or n for n, i in model.model_fields.items()]
    if len(loc) == 0:
        return [i.alias or n for n, i in Rule.model_fields.items()]
    return []


# ----------------------------------------------------------------- loading
def load_file(path: PathLike) -> Tuple[Optional[Rule], List[RuleProblem]]:
    """Parse and validate one rule file."""
    path = Path(path)
    shown = str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [RuleProblem(shown, f"cannot read file: {exc}")]
    try:
        node = yaml.compose(text)
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark else None
        return None, [RuleProblem(shown, f"not valid YAML: {exc}", line=line)]
    if not isinstance(data, dict):
        return None, [
            RuleProblem(shown, "a rule file holds one mapping (id, name, ...)")
        ]
    try:
        return Rule.model_validate(data), []
    except ValidationError as exc:
        problems = [
            RuleProblem(
                shown,
                _message(err),
                _field_path(err["loc"]),
                _line_of(node, err["loc"]),
            )
            for err in exc.errors()
        ]
        return None, problems


def semantic_problems(rule: Rule, path: PathLike) -> List[RuleProblem]:
    """Check beyond the schema that reference cases carry the needed inputs."""
    problems = []
    needed = rule_inputs(rule)
    for i, case in enumerate(rule.reference_cases):
        natal = case.natal or rule.natal
        field = f"reference_cases[{i}]"
        if "place" in needed and case.place is None:
            problems.append(
                RuleProblem(
                    str(path), "the rule uses the Lagna or sunrise; add a place", field
                )
            )
        if ("natal" in needed or "natal_place" in needed) and natal is None:
            problems.append(
                RuleProblem(
                    str(path),
                    "the rule uses a natal chart (dasha or transit-to-natal); add "
                    "natal: {moment, place} to the case or to the rule",
                    field,
                )
            )
        if "natal_place" in needed and natal is not None and natal.place is None:
            problems.append(
                RuleProblem(
                    str(path),
                    "the rule uses the natal Lagna; give the natal a place",
                    field,
                )
            )
    return problems


def load_rules(
    paths: Optional[Sequence[PathLike]] = None,
) -> Tuple[List[LoadedRule], List[RuleProblem]]:
    """Load every rule under ``paths``; return (rules, problems)."""
    loaded: List[LoadedRule] = []
    problems: List[RuleProblem] = []
    first_seen: Dict[str, Path] = {}
    for path in discover(paths):
        rule, errs = load_file(path)
        problems.extend(errs)
        if rule is None:
            continue
        if rule.id in first_seen:
            problems.append(
                RuleProblem(
                    str(path),
                    f"duplicate id '{rule.id}' (already used in {first_seen[rule.id]})",
                    "id",
                )
            )
            continue
        first_seen[rule.id] = path
        problems.extend(semantic_problems(rule, path))
        loaded.append(LoadedRule(rule, path))
    return loaded, problems


class RuleRegistry:
    """All rules, indexed by id, domain and tier."""

    def __init__(self, loaded: Iterable[LoadedRule]):
        """Index ``loaded``; ids must be unique."""
        self._loaded: Dict[str, LoadedRule] = {}
        self.by_domain: Dict[str, List[Rule]] = defaultdict(list)
        self.by_tier: Dict[str, List[Rule]] = defaultdict(list)
        for item in loaded:
            if item.rule.id in self._loaded:
                raise ValueError(f"duplicate rule id {item.rule.id!r}")
            self._loaded[item.rule.id] = item
            self.by_domain[item.rule.domain].append(item.rule)
            self.by_tier[item.rule.tier].append(item.rule)

    @classmethod
    def load(cls, paths: Optional[Sequence[PathLike]] = None) -> "RuleRegistry":
        """Load and validate; raise :class:`RuleLoadError` on any problem."""
        loaded, problems = load_rules(paths)
        if problems:
            raise RuleLoadError(problems)
        return cls(loaded)

    def __len__(self) -> int:
        """Return the number of rules."""
        return len(self._loaded)

    def __iter__(self) -> Iterator[Rule]:
        """Rules in id order."""
        return iter(self._loaded[k].rule for k in sorted(self._loaded))

    def __contains__(self, rule_id: object) -> bool:
        """Return True if a rule with this id is loaded."""
        return rule_id in self._loaded

    def get(self, rule_id: str) -> Rule:
        """Return the rule ``rule_id``; KeyError with a suggestion otherwise."""
        if rule_id not in self._loaded:
            raise KeyError(
                f"no rule '{rule_id}'." + suggest(rule_id, list(self._loaded))
            )
        return self._loaded[rule_id].rule

    def path_of(self, rule_id: str) -> Path:
        """Return the file a rule was loaded from."""
        return self._loaded[rule_id].path

    def filter(
        self,
        domain: Optional[str] = None,
        tier: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Rule]:
        """Rules matching every given criterion, in id order."""
        return [
            r
            for r in self
            if (domain is None or r.domain == domain)
            and (tier is None or r.tier == tier)
            and (status is None or r.status == status)
        ]


__all__ = [
    "LoadedRule",
    "RuleLoadError",
    "RuleProblem",
    "RuleRegistry",
    "default_rules_dir",
    "discover",
    "load_file",
    "load_rules",
    "semantic_problems",
]
