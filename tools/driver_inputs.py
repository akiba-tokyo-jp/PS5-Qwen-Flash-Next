# SPDX-License-Identifier: MIT
"""Validate the selected shared-driver source and exact profile artifact."""
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_driver(root, manifest_path, selected):
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != selected["revision"]:
        raise ValueError("Driver source revision differs from the dependency lock")
    for arguments in (["diff", "--quiet", "HEAD", "--"], ["diff", "--cached", "--quiet", "--"]):
        if subprocess.run(["git", "-C", str(root), *arguments], capture_output=True).returncode:
            raise ValueError("Tracked driver source has local changes")
    for entry in selected["source_files"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid driver source path")
        if sha(root / relative) != entry["sha256"]:
            raise ValueError("Driver integration source digest mismatch: " + entry["path"])
    if sha(manifest_path) != selected["profile_manifest_sha256"]:
        raise ValueError("Driver profile manifest differs from the dependency lock")
    profile = json.loads(manifest_path.read_text())
    required = {
        "schema": "ps5-selected-mesa-members-v1", "profile": selected["profile"],
        "mesa_commit": selected["mesa_revision"], "base_archive_sha256": selected["base_archive_sha256"],
        "profile_selected_explicitly": True, "capture_isa": selected["capture_isa"],
        "client_platform_allocator_members_preserved": True,
        "persistent_shader_and_pipeline_caches_must_be_disabled": True,
        "production_cache_identity_release_qualified": False,
        "source_checkout_modified": False, "console_execution": False, "CI": False,
    }
    if selected["persistent_caches_enabled"] or any(profile.get(key) != value for key, value in required.items()):
        raise ValueError("Driver profile or cache policy does not match the integration contract")
    if sorted(profile["changed_members"]) != sorted(selected["changed_members"]) or profile["patches"] != selected["patches"]:
        raise ValueError("Driver profile member or patch provenance differs")
    archive = manifest_path.parent / "libvulkan_radeon.experimental.a"
    digest = sha(archive)
    if digest != selected["archive_sha256"] or digest != profile["archive_sha256"]:
        raise ValueError("Driver archive digest mismatch")
    return {"repository": selected["repository"], "source_revision": revision, "profile": profile["profile"],
            "mesa_revision": profile["mesa_commit"], "archive_path": str(archive), "archive_sha256": digest,
            "profile_manifest_path": str(manifest_path), "profile_manifest_sha256": sha(manifest_path),
            "persistent_caches_disabled_required": True, "capture_isa": profile["capture_isa"],
            "changed_members": profile["changed_members"], "source_files": selected["source_files"]}
