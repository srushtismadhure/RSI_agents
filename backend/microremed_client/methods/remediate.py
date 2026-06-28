import methods.ThinkRemed.coordinator
import methods.SoloGen.generator


def remediate(client, runtime_envs, namespace, root_cause, failure_category, remediate_method):
    if remediate_method == "ThinkRemed":
        return methods.ThinkRemed.coordinator.remediate_failure(client, runtime_envs, namespace, root_cause, failure_category)
    elif remediate_method == "SoloGen":
        return methods.SoloGen.generator.remediate_failure(client, runtime_envs, namespace, root_cause, failure_category)
    else:
        raise ValueError(
            f"Unknown remediate_method: {remediate_method!r}. Expected 'ThinkRemed' or 'SoloGen'."
        )
