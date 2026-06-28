def get_probe_response(
        client: any,
        cmds: str,
) -> str:
    status, output = client.execute_probe(cmds)
    return output
