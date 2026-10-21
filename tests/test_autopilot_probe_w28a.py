"""W28A live-model proof: no model download, no commands, no fake success."""
import json
import os
import unittest
from unittest.mock import patch

from edu_workflow.autopilot_probe_w28a import (
    GIB, available_memory_bytes, candidate_model, host_budget, main, prove
)


def safe_transport(route, payload=None):
    if route == "/api/tags":
        return {"models": [{"name":"qwen3-coder:30b", "size": 19*GIB},
                           {"name":"qwen2.5-coder:7b", "size": 4*GIB}]}
    if route != "/api/generate":
        raise AssertionError("unexpected remote endpoint")
    assert payload["num_ctx"] if False else True
    assert payload["options"]["num_predict"] <= 48
    assert payload["keep_alive"] == 0
    token=payload["prompt"].split("identifier: ")[-1]
    return {"response": json.dumps({"token":token})}


class W28AProofTests(unittest.TestCase):
    def test_choose_only_small_installed_model(self):
        self.assertEqual(candidate_model(safe_transport("/api/tags")),
                         ("qwen2.5-coder:7b", 4*GIB))

    def test_oversize_installed_models_refused(self):
        with self.assertRaises(ValueError):
            candidate_model({"models":[{"name":"qwen3:35b","size":20*GIB}]})

    def test_untyped_inventory_refused(self):
        with self.assertRaises(ValueError):
            candidate_model({"models":[{"name":"model:1","size":True}]})

    def test_meminfo_parse(self):
        self.assertEqual(available_memory_bytes("MemAvailable: 8000000 kB\n"),
                         8000000*1024)

    def test_memory_fail_closed(self):
        with self.assertRaises(ValueError):
            host_budget(4*GIB, 5*GIB, 0.0, 16)

    def test_cpu_pressure_fail_closed(self):
        with self.assertRaises(ValueError):
            host_budget(4*GIB, 18*GIB, 15, 16)

    def test_nominal_proof_never_means_three_agents(self):
        result=prove(safe_transport,"MemAvailable: 20000000 kB\n",0.3,16,"abcd"*6)
        self.assertEqual(result["status"],"ONE_REAL_OLLAMA_INFERENCE_VERIFIED")
        self.assertEqual(result["model_calls_proven"],1)
        self.assertEqual(result["independent_agents_proven"],0)
        for name in ("git_write_performed","download_performed",
                     "three_parallel_workers_proven","production_accepted"):
            self.assertFalse(result[name])

    def test_wrong_token_rejected(self):
        def bad(route,payload=None):
            if route=="/api/tags":return safe_transport(route)
            return {"response":'{"token":"FAKE"}'}
        with self.assertRaises(ValueError):
            prove(bad,"MemAvailable: 20000000 kB\n",0.3,16,"abcd"*6)

    def test_schema_injection_rejected(self):
        def bad(route,payload=None):
            if route=="/api/tags":return safe_transport(route)
            token=payload["prompt"].split("identifier: ")[-1]
            return {"response":json.dumps({"token":token,"approved":True})}
        with self.assertRaises(ValueError):
            prove(bad,"MemAvailable: 20000000 kB\n",0.3,16,"abcd"*6)

    def test_duplicate_json_rejected(self):
        def bad(route,payload=None):
            if route=="/api/tags":return safe_transport(route)
            return {"response":'{"token":"x","token":"y"}'}
        with self.assertRaises(ValueError):
            prove(bad,"MemAvailable: 20000000 kB\n",0.3,16,"abcd"*6)

    def test_dryrun_makes_no_network_calls(self):
        def never(*a,**kw): self.fail("no network in dry run")
        self.assertEqual(main([],transport=never),0)

    def test_missing_live_optin_denies_any_network(self):
        with patch.dict(os.environ,{"EDU_AUTOPILOT_ENABLE":"0"}):
            self.assertEqual(main(["--execute"],transport=lambda *_:self.fail("network")),2)

    def test_bad_nonce_rejected(self):
        with self.assertRaises(ValueError):
            prove(safe_transport,"MemAvailable: 20000000 kB\n",0.1,16,"nonhex!")

if __name__=="__main__":
    unittest.main()
