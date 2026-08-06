from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class Manifest(BaseModel):
    pipeline_id: str
    latest_versions: dict[str, int] = {}
    artifact_index: list[dict] = []
    consumers: dict = {}
    version: int = 1


def _manifest_path(repo_workdir: Path, pipeline_id: str) -> Path:
    return repo_workdir / "pipelines" / pipeline_id / ".manifest.yaml"


def load_manifest(repo_workdir: Path, pipeline_id: str) -> Manifest | None:
    path = _manifest_path(repo_workdir, pipeline_id)
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text())
        if data is None:
            return None
        return Manifest(**data)
    except Exception:
        return None


def save_manifest(repo_workdir: Path, manifest: Manifest) -> None:
    path = _manifest_path(repo_workdir, manifest.pipeline_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = manifest.model_dump()
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def bump_version(manifest: Manifest, node_id: str) -> Manifest:
    new_latest = dict(manifest.latest_versions)
    new_latest[node_id] = new_latest.get(node_id, 0) + 1
    return Manifest(
        pipeline_id=manifest.pipeline_id,
        latest_versions=new_latest,
        artifact_index=list(manifest.artifact_index),
        consumers=dict(manifest.consumers),
        version=manifest.version + 1,
    )
