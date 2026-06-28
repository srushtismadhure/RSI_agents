import requests


class ChaosClient:
    def __init__(self, base_url: str):
        """
        :param base_url: The base URL of the Flask server, e.g. "http://127.0.0.1:5000"
        """
        self.base_url = base_url.rstrip("/")

    def _post(self, endpoint: str, payload: dict) -> dict:
        """Unified POST request with consistent response handling."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=30)
        except Exception as e:
            raise RuntimeError(f"❌ Failed to connect to {url}: {e}")

        if response.status_code == 400:
            raise ValueError(f"🚫 Invalid parameters for {endpoint}: {response.text.strip()}")
        elif response.status_code == 500:
            return {"status": False, "output": response.json().get("message", response.text)}
        elif response.status_code == 200:
            return {"status": True, "output": response.json().get("message", response.text)}
        else:
            raise RuntimeError(f"⚠️ Unexpected response ({response.status_code}): {response.text}")

    # -------------------- Interface Wrappers --------------------

    def deploy_env(self, env_name: str) -> dict:
        return self._post("deploy_env", {"env_name": env_name})

    def inject_failure(self, failure_type: str, target_pod: str, target_namespace: str) -> dict:
        return self._post("inject_failure", {
            "failure_type": failure_type,
            "target_pod": target_pod,
            "target_namespace": target_namespace
        })

    def check_status(self, target_namespace: str, app_label: str, failure_type: str, timeout: int = 0) -> dict:
        return self._post("check_status", {
            "target_namespace": target_namespace,
            "app_label": app_label,
            "failure_type": failure_type,
            "timeout": timeout
        })

    def stop_injection(self, failure_type: str, target_namespace: str) -> dict:
        return self._post("stop_injection", {
            "failure_type": failure_type,
            "target_namespace": target_namespace
        })

    def restore_by_original_manifest(self, target_namespace: str, target_pod: str, manifest_path: str) -> dict:
        return self._post("restore_by_original_manifest", {
            "target_namespace": target_namespace,
            "target_pod": target_pod,
            "manifest_path": manifest_path
        })

    def execute_playbook(self, playbook: str) -> dict:
        return self._post("execute_playbook", {"playbook": playbook})

    def execute_probe(self, cmds: list[str]) -> dict:
        return self._post("execute_probe", {"cmds": cmds})
