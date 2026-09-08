import json
from pathlib import Path
import tempfile
import unittest

from source.lawspace.domains import load_domain_plugin_manifests, _registry_from_plugin_manifest
from source.lawspace.domain_plugins import ScienceDomainPluginRegistry
from source.lawspace.scientific_rules import CommonScientificRulesCore, OWNER_ID as COMMON_OWNER


def _doc():
    return {
        "schema": "phi-domain-plugin-manifest/v1",
        "domain_id": "test_science",
        "domain_role": "natural_science",
        "description_ru": "test",
        "common_rules_owner": COMMON_OWNER,
        "axes": [{
            "axis_id": "x", "description_ru": "x", "value_kind": "TEXT",
            "allowed_values": [], "required_for": [], "forbidden_for": [], "provenance": "TEST"
        }],
        "entity_profiles": [], "constraints": [], "owner": {},
    }


class DomainPluginArchitectureTests(unittest.TestCase):
    def _load(self, doc):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "test.json").write_text(json.dumps(doc), encoding="utf-8")
            return load_domain_plugin_manifests(td)

    def test_minimal_manifest_loads_without_central_registry_edit(self):
        docs = self._load(_doc())
        self.assertIn("test_science", docs)
        reg = _registry_from_plugin_manifest(docs["test_science"])
        self.assertEqual(reg.axis_count, 1)

    def test_manifest_must_delegate_common_rules(self):
        doc = _doc(); doc["common_rules_owner"] = "LOCAL-RULES"
        with self.assertRaises(ValueError):
            self._load(doc)

    def test_manifest_cannot_shadow_generic_rules(self):
        doc = _doc(); doc["generic_rules"] = {"promotion": True}
        with self.assertRaises(ValueError):
            self._load(doc)

    def test_duplicate_axes_fail_closed(self):
        doc = _doc(); doc["axes"] = doc["axes"] * 2
        with self.assertRaises(ValueError):
            self._load(doc)

    def test_partial_owner_declaration_fails(self):
        doc = _doc(); doc["owner"] = {"module": "source.lawspace.x"}
        with self.assertRaises(ValueError):
            self._load(doc)

    def test_pharmaceutical_plugin_delegation_is_ready(self):
        out = ScienceDomainPluginRegistry().get_domain_contract("pharmaceutical")
        self.assertEqual(out["domain_owner_status"], "READY")
        self.assertTrue(out["common_rule_delegation"]["qualified"])

    def test_common_rules_is_router_not_parallel_solver(self):
        c = CommonScientificRulesCore().contract()
        self.assertEqual(c["implementation_policy"], "ROUTING_CONTRACT_ONLY_NO_PARALLEL_SOLVER")
        self.assertTrue(c["generic_rules"]["unknown_or_unexecuted_gates_fail_closed"])


if __name__ == "__main__":
    unittest.main()
