def execute_playbook_and_get_response(client: any, playbook: str):
    """
    Execute a given Ansible playbook and return its execution result.

    Args:
        client: ChaosClient
        playbook (str): YAML content of the Ansible playbook.

    Returns:
        (bool, str): A tuple where:
            - bool indicates whether the execution was successful.
            - str contains stdout (on success) or detailed error output (on failure).
    """
    return client.execute_playbook(playbook)
