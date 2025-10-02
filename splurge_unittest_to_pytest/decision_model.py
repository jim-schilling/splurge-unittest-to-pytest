"""Decision model for multi-pass transformation analysis.

This module provides data structures to represent transformation decisions
and evidence collected during the analysis phase of the multi-pass pipeline.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, TypedDict


class Stats(TypedDict):
    total_modules: int
    total_classes: int
    total_functions: int
    strategy_counts: dict[str, int]
    evidence_rich_functions: int
    accumulator_detected: int


__all__ = [
    "CaplogAliasMetadata",
    "FunctionProposal",
    "ClassProposal",
    "ModuleProposal",
    "DecisionModel",
]


@dataclass
class CaplogAliasMetadata:
    """Metadata about caplog/assertLogs alias usage in a function."""

    alias_name: str
    """The alias name used in the with statement (e.g., 'log_ctx')"""

    used_as_records: bool
    """Whether the alias is used with .records attribute"""

    used_as_messages: bool
    """Whether the alias is used with .messages attribute or .output"""

    locations: list[str]
    """List of code locations where this alias is used"""

    def __post_init__(self) -> None:
        """Validate the metadata after initialization."""
        if not self.used_as_records and not self.used_as_messages:
            logging.warning(f"CaplogAliasMetadata for '{self.alias_name}' has no usage detected")


@dataclass
class FunctionProposal:
    """Proposal for how to transform a specific function."""

    function_name: str
    """Name of the function being analyzed"""

    recommended_strategy: Literal["parametrize", "subtests", "keep-loop"]
    """Recommended transformation strategy"""

    loop_var_name: str | None = None
    """Name of the loop variable if parametrize is recommended"""

    iterable_origin: Literal["literal", "name", "call"] | None = None
    """How the iterable was created"""

    accumulator_mutated: bool = False
    """Whether the iterable source is mutated (accumulator pattern)"""

    caplog_aliases: list[CaplogAliasMetadata] = field(default_factory=list)
    """Caplog/assertLogs aliases used in this function"""

    evidence: list[str] = field(default_factory=list)
    """Evidence and reasoning for this recommendation"""

    def add_evidence(self, evidence_line: str) -> None:
        """Add evidence for this proposal."""
        if evidence_line not in self.evidence:
            self.evidence.append(evidence_line)

    def is_confident(self) -> bool:
        """Check if this proposal has sufficient evidence."""
        return len(self.evidence) >= 1


@dataclass
class ClassProposal:
    """Aggregated proposal for transforming a test class."""

    class_name: str
    """Name of the class being analyzed"""

    function_proposals: dict[str, FunctionProposal]
    """Proposals for each function in this class"""

    class_fixtures: list[str] = field(default_factory=list)
    """Class-level fixtures detected"""

    class_setup_methods: list[str] = field(default_factory=list)
    """SetUp/tearDown methods detected"""

    def add_function_proposal(self, proposal: FunctionProposal) -> None:
        """Add a function proposal to this class."""
        self.function_proposals[proposal.function_name] = proposal

    def get_strategy_consensus(self) -> str | None:
        """Get the most common strategy across all functions."""
        if not self.function_proposals:
            return None

        strategies = [p.recommended_strategy for p in self.function_proposals.values()]
        return max(set(strategies), key=strategies.count) if strategies else None


@dataclass
class ModuleProposal:
    """Proposal for transforming an entire module."""

    module_name: str
    """Name of the module being analyzed"""

    class_proposals: dict[str, ClassProposal]
    """Proposals for each class in this module"""

    module_fixtures: list[str] = field(default_factory=list)
    """Module-level fixtures detected"""

    module_imports: list[str] = field(default_factory=list)
    """Module-level imports detected"""

    top_level_assignments: dict[str, Any] = field(default_factory=dict)
    """Top-level variable assignments detected"""

    def add_class_proposal(self, proposal: ClassProposal) -> None:
        """Add a class proposal to this module."""
        self.class_proposals[proposal.class_name] = proposal

    def get_all_function_proposals(self) -> dict[str, FunctionProposal]:
        """Get all function proposals from all classes."""
        all_proposals = {}
        for class_proposal in self.class_proposals.values():
            all_proposals.update(class_proposal.function_proposals)
        return all_proposals


@dataclass
class DecisionModel:
    """Complete decision model for a module's transformation."""

    module_proposals: dict[str, ModuleProposal]
    """Proposals for each module analyzed"""

    def add_module_proposal(self, proposal: ModuleProposal) -> None:
        """Add a module proposal to this model."""
        self.module_proposals[proposal.module_name] = proposal

    def save_to_file(self, filepath: str | Path) -> None:
        """Save the decision model to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclasses to dict for JSON serialization
        data = {
            "module_proposals": {
                name: self._proposal_to_dict(proposal) for name, proposal in self.module_proposals.items()
            }
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filepath: str | Path) -> None:
        """Load a decision model from a JSON file."""
        filepath = Path(filepath)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        self.module_proposals = {
            name: self._dict_to_proposal(data["module_proposals"][name]) for name in data["module_proposals"]
        }

    def _proposal_to_dict(self, proposal: ModuleProposal) -> dict:
        """Convert a ModuleProposal to dict for JSON serialization."""
        return {
            "module_name": proposal.module_name,
            "class_proposals": {
                name: {
                    "class_name": class_prop.class_name,
                    "function_proposals": {
                        fname: asdict(func_prop) for fname, func_prop in class_prop.function_proposals.items()
                    },
                    "class_fixtures": class_prop.class_fixtures,
                    "class_setup_methods": class_prop.class_setup_methods,
                }
                for name, class_prop in proposal.class_proposals.items()
            },
            "module_fixtures": proposal.module_fixtures,
            "module_imports": proposal.module_imports,
            "top_level_assignments": proposal.top_level_assignments,
        }

    def _dict_to_proposal(self, data: dict) -> ModuleProposal:
        """Convert dict back to ModuleProposal."""
        # This is a simplified reconstruction - in practice we'd want more robust deserialization
        return ModuleProposal(
            module_name=data["module_name"],
            class_proposals={},  # Simplified for now
            module_fixtures=data.get("module_fixtures", []),
            module_imports=data.get("module_imports", []),
            top_level_assignments=data.get("top_level_assignments", {}),
        )

    def validate(self) -> list[str]:
        """Validate the decision model for consistency and completeness.

        Returns:
            List of validation warnings or errors.
        """
        warnings = []

        for _module_name, module_prop in self.module_proposals.items():
            warnings.extend(self._validate_module(module_prop))

        return warnings

    def _validate_module(self, module_prop: ModuleProposal) -> list[str]:
        """Validate a module proposal."""
        warnings = []

        # Check for functions with no evidence
        for class_name, class_prop in module_prop.class_proposals.items():
            for func_name, func_prop in class_prop.function_proposals.items():
                if not func_prop.evidence:
                    warnings.append(
                        f"Function {func_name} in class {class_name} has no evidence for strategy '{func_prop.recommended_strategy}'"
                    )

                # Check for accumulator detection inconsistencies
                if func_prop.accumulator_mutated and func_prop.recommended_strategy != "subtests":
                    warnings.append(
                        f"Function {func_name} has accumulator_mutated=True but strategy is '{func_prop.recommended_strategy}' (should be 'subtests')"
                    )

        return warnings

    def detect_conflicts(self) -> list[str]:
        """Detect conflicts in the decision model.

        Returns:
            List of conflict descriptions.
        """
        conflicts = []

        for _module_name, module_prop in self.module_proposals.items():
            conflicts.extend(self._detect_module_conflicts(module_prop))

        return conflicts

    def _detect_module_conflicts(self, module_prop: ModuleProposal) -> list[str]:
        """Detect conflicts within a module proposal."""
        conflicts = []

        # Check for functions with conflicting strategies in the same class
        for class_name, class_prop in module_prop.class_proposals.items():
            strategies = [p.recommended_strategy for p in class_prop.function_proposals.values()]

            # Check if there are conflicting strategies that should be reconciled
            if "parametrize" in strategies and "subtests" in strategies:
                conflicts.append(
                    f"Class {class_name} has mixed strategies (parametrize + subtests) - may need reconciliation"
                )

        return conflicts

    def get_statistics(self) -> Stats:
        """Get statistics about the decision model.

        Returns:
            Dictionary with various statistics.
        """
        stats: Stats = {
            "total_modules": len(self.module_proposals),
            "total_classes": 0,
            "total_functions": 0,
            "strategy_counts": {"parametrize": 0, "subtests": 0, "keep-loop": 0},
            "evidence_rich_functions": 0,
            "accumulator_detected": 0,
        }

        for module_prop in self.module_proposals.values():
            stats["total_classes"] += len(module_prop.class_proposals)

            for class_prop in module_prop.class_proposals.values():
                stats["total_functions"] += len(class_prop.function_proposals)

                for func_prop in class_prop.function_proposals.values():
                    strategy = func_prop.recommended_strategy
                    if strategy in stats["strategy_counts"]:
                        stats["strategy_counts"][strategy] += 1

                    if len(func_prop.evidence) >= 2:
                        stats["evidence_rich_functions"] += 1

                    if func_prop.accumulator_mutated:
                        stats["accumulator_detected"] += 1

        return stats

    def to_dict(self) -> dict[str, Any]:
        """Convert decision model to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionModel:
        """Create decision model from dictionary."""
        return cls(**data)

    def __str__(self) -> str:
        """String representation for debugging."""
        lines = [f"DecisionModel with {len(self.module_proposals)} modules:"]

        for module_name, module_prop in self.module_proposals.items():
            lines.append(f"  {module_name}:")
            lines.append(f"    Classes: {len(module_prop.class_proposals)}")
            lines.append(f"    Module fixtures: {len(module_prop.module_fixtures)}")

            for class_name, class_prop in module_prop.class_proposals.items():
                lines.append(f"      {class_name}: {len(class_prop.function_proposals)} functions")

        return "\n".join(lines)
