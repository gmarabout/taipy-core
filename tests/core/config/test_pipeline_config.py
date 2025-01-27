# Copyright 2023 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

import os
from unittest import mock

import pytest

from taipy.config.config import Config
from tests.core.utils.named_temporary_file import NamedTemporaryFile


def _configure_pipeline_in_toml():
    return NamedTemporaryFile(
        content="""
[TAIPY]

[TASK.task1]
function = "builtins.print:function"
inputs = []
outputs = []

[TASK.task2]
function = "builtins.print:function"
inputs = []
outputs = []

[PIPELINE.pipelines1]
tasks = [ "task1:SECTION", "task2:SECTION"]
    """
    )


def _check_tasks_instance(task_id, pipeline_id):
    """Check if the task instance in the pipeline config correctly points to the Config._applied_config,
    not the Config._python_config or the Config._file_config
    """
    task_config_applied_instance = Config.tasks[task_id]
    for task in Config.pipelines[pipeline_id].tasks:
        if task.id == task_id:
            task_config_instance_via_pipeline = task

    task_config_python_instance = None
    if Config._python_config._sections.get("TASK", None):
        task_config_python_instance = Config._python_config._sections["TASK"][task_id]

    task_config_file_instance = None
    if Config._file_config._sections.get("TASK", None):
        task_config_file_instance = Config._file_config._sections["TASK"][task_id]

    assert task_config_python_instance is not task_config_applied_instance
    assert task_config_python_instance is not task_config_instance_via_pipeline
    assert task_config_file_instance is not task_config_applied_instance
    assert task_config_file_instance is not task_config_instance_via_pipeline
    assert task_config_instance_via_pipeline is task_config_applied_instance


def test_task_instance_when_configure_pipeline_in_python():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    Config.configure_pipeline("pipelines1", [task1_config, task2_config])

    _check_tasks_instance("task1", "pipelines1")
    _check_tasks_instance("task2", "pipelines1")


def test_task_instance_when_configure_pipeline_by_loading_toml():
    toml_config = _configure_pipeline_in_toml()
    Config.load(toml_config.filename)

    _check_tasks_instance("task1", "pipelines1")
    _check_tasks_instance("task2", "pipelines1")


def test_task_instance_when_configure_pipeline_by_overriding_toml():
    toml_config = _configure_pipeline_in_toml()
    Config.override(toml_config.filename)

    _check_tasks_instance("task1", "pipelines1")
    _check_tasks_instance("task2", "pipelines1")


def test_pipeline_config_creation():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    pipeline_config = Config.configure_pipeline("pipelines1", [task1_config, task2_config])

    assert list(Config.pipelines) == ["default", pipeline_config.id]

    pipeline2_config = Config.configure_pipeline("pipelines2", [task1_config, task2_config])
    assert list(Config.pipelines) == ["default", pipeline_config.id, pipeline2_config.id]


def test_pipeline_count():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    Config.configure_pipeline("pipelines1", [task1_config, task2_config])
    assert len(Config.pipelines) == 2

    Config.configure_pipeline("pipelines2", [task1_config, task2_config])
    assert len(Config.pipelines) == 3

    Config.configure_pipeline("pipelines3", [task1_config, task2_config])
    assert len(Config.pipelines) == 4


def test_pipeline_getitem():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    pipeline_config_id = "pipelines1"
    pipeline = Config.configure_pipeline(pipeline_config_id, [task1_config, task2_config])

    assert Config.pipelines[pipeline_config_id].id == pipeline.id
    assert Config.pipelines[pipeline_config_id]._tasks == pipeline._tasks
    assert Config.pipelines[pipeline_config_id].properties == pipeline.properties


def test_pipeline_creation_no_duplication():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    Config.configure_pipeline("pipelines1", [task1_config, task2_config])

    assert len(Config.pipelines) == 2

    Config.configure_pipeline("pipelines1", [task1_config, task2_config])
    assert len(Config.pipelines) == 2


def test_pipeline_config_with_env_variable_value():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    with mock.patch.dict(os.environ, {"FOO": "bar"}):
        Config.configure_pipeline("pipeline_name", [task1_config, task2_config], prop="ENV[FOO]")
        assert Config.pipelines["pipeline_name"].prop == "bar"
        assert Config.pipelines["pipeline_name"].properties["prop"] == "bar"
        assert Config.pipelines["pipeline_name"]._properties["prop"] == "ENV[FOO]"


def test_clean_config():
    task1_config = Config.configure_task("task1", print, [], [])
    task2_config = Config.configure_task("task2", print, [], [])
    pipeline1_config = Config.configure_pipeline("id1", [task1_config, task2_config])
    pipeline2_config = Config.configure_pipeline("id2", [task2_config, task1_config])

    assert Config.pipelines["id1"] is pipeline1_config
    assert Config.pipelines["id2"] is pipeline2_config

    pipeline1_config._clean()
    pipeline2_config._clean()

    # Check if the instance before and after _clean() is the same
    assert Config.pipelines["id1"] is pipeline1_config
    assert Config.pipelines["id2"] is pipeline2_config

    assert pipeline1_config.id == "id1"
    assert pipeline2_config.id == "id2"
    assert pipeline1_config.tasks == pipeline2_config.tasks == []
    assert pipeline1_config.properties == pipeline2_config.properties == {}


def test_pipeline_config_configure_deprecated():
    with pytest.warns(DeprecationWarning):
        Config.configure_pipeline("pipeline_id", [])

    with pytest.warns(DeprecationWarning):
        Config.set_default_pipeline_configuration([])
