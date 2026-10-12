from __future__ import annotations

from pathlib import Path

import pytest

from ave.samples import generate_samples


@pytest.fixture(scope="session")
def samples(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("samples")
    return generate_samples(root)
