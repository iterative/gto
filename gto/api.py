import pandas as pd

from gto.registry import GitRegistry


def show(repo: str, dataframe: bool = False):
    """Show current registry state"""

    reg = GitRegistry.from_repo(repo)
    models_state = {
        o.name: {
            "version": o.latest_version,
            "environment": {
                l: o.latest_labels[l].version
                if o.latest_labels[l] is not None
                else None
                for l in o.unique_labels
            },
        }
        for o in reg.state.objects.values()
    }
    if dataframe:
        result = {
            ("", "latest"): {name: d["version"] for name, d in models_state.items()}
        }
        for name, details in models_state.items():
            for env, ver in details["environment"].items():
                result[("environment", env)] = {
                    **result.get(("environment", env), {}),
                    **{name: ver},
                }
        result_df = pd.DataFrame(result)
        result_df.columns = pd.MultiIndex.from_tuples(result_df.columns)
        return result_df
    return models_state


def audit_registration(repo: str, dataframe: bool = False):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)

    model_registration_audit_trail = [
        {
            "name": o.name,
            "version": v.name,
            "creation_date": v.creation_date,
            "author": v.author,
            "commit_hexsha": v.commit_hexsha,
            "unregistered_date": v.unregistered_date,
        }
        for o in reg.state.objects.values()
        for v in o.versions
    ]
    if dataframe:
        return (
            pd.DataFrame(model_registration_audit_trail)
            .sort_values("creation_date", ascending=False)
            .set_index(["creation_date", "name"])
        )
    return model_registration_audit_trail


def audit_promotion(repo: str, dataframe: bool = False):
    """Audit registry state"""
    reg = GitRegistry.from_repo(repo)
    label_assignment_audit_trail = [
        {
            "name": o.name,
            "label": l.name,
            "version": l.version,
            "creation_date": l.creation_date,
            "author": l.author,
            "commit_hexsha": l.commit_hexsha,
            "unregistered_date": l.unregistered_date,
        }
        for o in reg.state.objects.values()
        for l in o.labels
    ]
    if dataframe:
        return (
            pd.DataFrame(label_assignment_audit_trail)
            .sort_values("creation_date", ascending=False)
            .set_index(["creation_date", "name"])
        )
    return label_assignment_audit_trail
