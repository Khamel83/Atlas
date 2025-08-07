import os
import shutil

import pytest


@pytest.fixture(scope="session", autouse=True)
def create_output_dir():
    original_cwd = os.getcwd()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(project_root)

    output_path = "output"
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    yield

    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.chdir(original_cwd)
