"""Tests for devfile path resolution and default loading."""

from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from nodes import config_loader


class TestResolveDevfilePath:
    def test_bare_filename_uses_data_directory(self):
        assert config_loader.resolve_devfile_path(
            "virtualconfig.yaml"
        ) == Path("data/virtualconfig.yaml")

    def test_relative_data_path_preserved(self):
        assert config_loader.resolve_devfile_path(
            "data/mqtt-devices.yaml"
        ) == Path("data/mqtt-devices.yaml")

    def test_absolute_path_preserved(self):
        abs_path = "/usr/home/admin/mqtt/virtualconfig.yaml"
        assert config_loader.resolve_devfile_path(abs_path) == Path(abs_path)


class TestLoadDevfileConfig:
    def test_empty_devfile_uses_default(self, tmp_path, monkeypatch):
        default_file = tmp_path / "data" / "mqtt-devices.yaml"
        default_file.parent.mkdir()
        default_file.write_text(
            yaml.dump({"devices": [{"id": "d1", "type": "switch"}]})
        )
        monkeypatch.chdir(tmp_path)

        controller = Mock()
        controller.Parameters = {"devfile": ""}

        assert config_loader.load_devfile_config(controller) is True
        assert controller.devlist == [{"id": "d1", "type": "switch"}]

    def test_bare_filename_resolves_under_data(self, tmp_path, monkeypatch):
        data_file = tmp_path / "data" / "virtualconfig.yaml"
        data_file.parent.mkdir()
        data_file.write_text(
            yaml.dump({"devices": [{"id": "v1", "type": "switch"}]})
        )
        monkeypatch.chdir(tmp_path)

        controller = Mock()
        controller.Parameters = {"devfile": "virtualconfig.yaml"}

        assert config_loader.load_devfile_config(controller) is True
        assert controller.devlist[0]["id"] == "v1"
