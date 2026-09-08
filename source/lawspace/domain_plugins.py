"""Declarative science-domain plugin registry.

A plugin manifest declares axes and the optional domain-specific owner. Generic
scientific rules are always delegated to CommonScientificRulesCore.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Mapping

from .domains import load_domain_plugin_manifests, DOMAIN_REGISTRIES
from .scientific_rules import CommonScientificRulesCore, OWNER_ID as COMMON_RULES_OWNER
from .schema import digest_payload

OWNER_ID = "SCIENCE-DOMAIN-PLUGIN-REGISTRY/1.0.0"
SCHEMA = "phi-science-domain-plugin-registry/v1"


class ScienceDomainPluginRegistry:
    owner_id = OWNER_ID

    def manifests(self, path: str | Path | None = None) -> Mapping[str, Mapping[str, Any]]:
        return load_domain_plugin_manifests(path)

    def list_plugins(self, path: str | Path | None = None) -> list[Mapping[str, Any]]:
        rows = []
        for domain_id, doc in sorted(self.manifests(path).items()):
            registry = DOMAIN_REGISTRIES.get(domain_id)
            rows.append({
                "domain_id": domain_id,
                "domain_role": doc.get("domain_role"),
                "axis_count": None if registry is None else registry.axis_count,
                "owner": dict(doc.get("owner", {}) or {}),
                "common_rules_owner": doc.get("common_rules_owner"),
            })
        return rows

    def contract(self, path: str | Path | None = None) -> Mapping[str, Any]:
        manifests = self.manifests(path)
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "common_rules": CommonScientificRulesCore().contract(),
            "plugin_count": len(manifests),
            "plugins": self.list_plugins(path),
            "installation_contract": {
                "manifest_schema": "phi-domain-plugin-manifest/v1",
                "manifest_location": "data/domains/*.json",
                "generic_rules_owner": COMMON_RULES_OWNER,
                "restart_required_after_manifest_change": True,
                "central_domains_py_edit_required_for_new_plugin": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def get_domain_contract(self, domain_id: str, path: str | Path | None = None) -> Mapping[str, Any]:
        doc = dict(self.manifests(path)[domain_id])
        owner = dict(doc.get("owner", {}) or {})
        module_name = str(owner.get("module", "")).strip()
        class_name = str(owner.get("class", "")).strip()
        if not module_name or not class_name:
            return {
                "domain_id": domain_id,
                "manifest": doc,
                "common_scientific_rules": CommonScientificRulesCore().contract(),
                "domain_owner_status": "NO_DOMAIN_SPECIFIC_OWNER_DECLARED",
            }
        cls = getattr(importlib.import_module(module_name), class_name)
        domain_contract = cls().contract()
        delegation = CommonScientificRulesCore().validate_domain_delegation(domain_contract)
        return {
            "domain_id": domain_id,
            "manifest": doc,
            "domain_contract": domain_contract,
            "common_rule_delegation": delegation,
            "domain_owner_status": "READY" if delegation["qualified"] else "BLOCKED_COMMON_RULE_DELEGATION",
        }
