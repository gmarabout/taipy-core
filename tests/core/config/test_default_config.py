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
from src.taipy.core.config import CoreSection
from src.taipy.core.config.data_node_config import DataNodeConfig
from src.taipy.core.config.job_config import JobConfig
from src.taipy.core.config.migration_config import MigrationConfig
from src.taipy.core.config.pipeline_config import PipelineConfig
from src.taipy.core.config.scenario_config import ScenarioConfig
from src.taipy.core.config.task_config import TaskConfig
from taipy.config._config import _Config
from taipy.config.common.scope import Scope
from taipy.config.config import Config
from taipy.config.global_app.global_app_config import GlobalAppConfig


def _test_default_job_config(job_config: JobConfig):
    assert job_config is not None
    assert job_config.mode == JobConfig._DEFAULT_MODE


def _test_default_core_section(core_section: CoreSection):
    assert core_section is not None
    assert core_section.mode == CoreSection._DEFAULT_MODE
    assert core_section.version_number == ""
    assert not core_section.force
    assert not core_section.clean_entities
    assert core_section.root_folder == "./taipy/"
    assert core_section.storage_folder == ".data/"
    assert core_section.repository_type == "filesystem"
    assert core_section.repository_properties == {}
    assert len(core_section.properties) == 0


def _test_default_data_node_config(dn_config: DataNodeConfig):
    assert dn_config is not None
    assert dn_config.id is not None
    assert dn_config.storage_type == "pickle"
    assert dn_config.scope == Scope.SCENARIO
    assert dn_config.validity_period is None
    assert len(dn_config.properties) == 0  # type: ignore


def _test_default_task_config(task_config: TaskConfig):
    assert task_config is not None
    assert task_config.id is not None
    assert task_config.input_configs == []
    assert task_config.output_configs == []
    assert task_config.function is None
    assert not task_config.skippable
    assert len(task_config.properties) == 0  # type: ignore


def _test_default_pipeline_config(pipeline_config: PipelineConfig):
    assert pipeline_config is not None
    assert pipeline_config.id is not None
    assert pipeline_config.task_configs == []
    assert len(pipeline_config.properties) == 0  # type: ignore


def _test_default_scenario_config(scenario_config: ScenarioConfig):
    assert scenario_config is not None
    assert scenario_config.id is not None
    assert scenario_config.pipeline_configs == []
    assert len(scenario_config.properties) == 0  # type: ignore


def _test_default_version_migration_config(version_migration_config: MigrationConfig):
    assert version_migration_config is not None
    assert version_migration_config.migration_fcts == {}
    assert len(version_migration_config.properties) == 0  # type: ignore


def _test_default_global_app_config(global_config: GlobalAppConfig):
    assert global_config is not None
    assert not global_config.notification
    assert len(global_config.properties) == 0


def test_default_configuration():
    default_config = Config._default_config
    assert default_config._global_config is not None
    _test_default_global_app_config(default_config._global_config)
    _test_default_global_app_config(Config.global_config)
    _test_default_global_app_config(GlobalAppConfig().default_config())

    assert default_config._unique_sections is not None
    assert len(default_config._unique_sections) == 3
    assert len(default_config._sections) == 4

    _test_default_job_config(default_config._unique_sections[JobConfig.name])
    _test_default_job_config(Config.job_config)
    _test_default_job_config(JobConfig().default_config())

    _test_default_version_migration_config(default_config._unique_sections[MigrationConfig.name])
    _test_default_version_migration_config(Config.migration_functions)
    _test_default_version_migration_config(MigrationConfig.default_config())

    _test_default_core_section(default_config._unique_sections[CoreSection.name])
    _test_default_core_section(Config.core)
    _test_default_core_section(CoreSection().default_config())

    _test_default_data_node_config(default_config._sections[DataNodeConfig.name][_Config.DEFAULT_KEY])
    _test_default_data_node_config(Config.data_nodes[_Config.DEFAULT_KEY])
    _test_default_data_node_config(DataNodeConfig.default_config())
    assert len(default_config._sections[DataNodeConfig.name]) == 1
    assert len(Config.data_nodes) == 1

    _test_default_task_config(default_config._sections[TaskConfig.name][_Config.DEFAULT_KEY])
    _test_default_task_config(Config.tasks[_Config.DEFAULT_KEY])
    _test_default_task_config(TaskConfig.default_config())
    assert len(default_config._sections[TaskConfig.name]) == 1
    assert len(Config.tasks) == 1

    _test_default_pipeline_config(default_config._sections[PipelineConfig.name][_Config.DEFAULT_KEY])
    _test_default_pipeline_config(Config.pipelines[_Config.DEFAULT_KEY])
    _test_default_pipeline_config(PipelineConfig.default_config())
    assert len(default_config._sections[PipelineConfig.name]) == 1
    assert len(Config.pipelines) == 1

    _test_default_scenario_config(default_config._sections[ScenarioConfig.name][_Config.DEFAULT_KEY])
    _test_default_scenario_config(Config.scenarios[_Config.DEFAULT_KEY])
    _test_default_scenario_config(ScenarioConfig.default_config())
    assert len(default_config._sections[ScenarioConfig.name]) == 1
    assert len(Config.scenarios) == 1
