from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml


class TaxonomyAdapter:
    """Provide a stable API for taxonomy/fallback rules."""

    def __init__(self, use_taxonomy: bool = False) -> None:
        self.use_taxonomy = use_taxonomy
        self._rules = self._load_taxonomy_rules() if use_taxonomy else self._load_fallback_rules()

    @property
    def rule_source(self) -> str:
        return self._rules.get("rule_source", "fallback")

    @property
    def rule_version(self) -> str:
        return self._rules.get("rule_version", "v1")

    def get_personas(self, categories: list[str]) -> list[dict[str, Any]]:
        personas: list[dict[str, Any]] = []
        pools = self._rules.get("personas", {})
        for cat in categories:
            personas.extend(pools.get(cat, []))
        return personas

    def pick_persona(self, category: str, seed: int) -> dict[str, Any]:
        pool = self._rules.get("personas", {}).get(category, [])
        if not pool:
            return {
                "id": f"default_{category.lower()}",
                "role": category,
                "motivation": "基础传播",
                "style": "占位画像",
                "category": category,
            }
        rng = random.Random(seed)
        return rng.choice(pool)

    def get_operation_whitelist(self, persona: dict[str, Any]) -> list[str]:
        category = str(persona.get("category", "Amplifier"))
        return self._rules.get("operation_whitelist", {}).get(category, [])

    def get_operation_layer(self, operation: str) -> str:
        return str(self._rules.get("operation_layer", {}).get(operation, "text"))

    def get_shift_prior(self, persona: dict[str, Any], gap_type: str) -> str:
        category = str(persona.get("category", "Amplifier"))
        priors = self._rules.get("shift_prior", {}).get(category, {})
        return str(priors.get(gap_type, "minor"))

    def get_role_transition_prior(self, parent_category: str) -> dict[str, float]:
        configured = self._rules.get("role_transition_prior", {}).get(parent_category)
        categories = ("Amplifier", "Analyst", "Bridger", "Adverser")
        if isinstance(configured, dict):
            parsed: dict[str, float] = {}
            for key in categories:
                raw = configured.get(key, 0.0)
                try:
                    parsed[key] = float(raw)
                except Exception:
                    parsed[key] = 0.0
            total = sum(parsed.values())
            if total > 0:
                return parsed
        # Fallback defaults aligned with taxonomy F2 trend.
        defaults: dict[str, dict[str, float]] = {
            "Bridger": {"Amplifier": 0.45, "Bridger": 0.30, "Analyst": 0.18, "Adverser": 0.07},
            "Amplifier": {"Amplifier": 0.42, "Bridger": 0.24, "Analyst": 0.22, "Adverser": 0.12},
            "Analyst": {"Amplifier": 0.40, "Bridger": 0.24, "Analyst": 0.20, "Adverser": 0.16},
            "Adverser": {"Amplifier": 0.33, "Bridger": 0.27, "Analyst": 0.20, "Adverser": 0.20},
        }
        return defaults.get(parent_category, defaults["Bridger"])

    @staticmethod
    def _load_taxonomy_rules() -> dict[str, Any]:
        rule_path = Path(__file__).resolve().parents[1] / "config" / "taxonomy_rules_v3.yaml"
        with rule_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data

    @staticmethod
    def _load_fallback_rules() -> dict[str, Any]:
        rule_path = Path(__file__).resolve().parents[1] / "config" / "fallback_rules.yaml"
        with rule_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data

