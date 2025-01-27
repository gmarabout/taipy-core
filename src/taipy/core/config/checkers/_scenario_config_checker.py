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

from taipy.config import Config
from taipy.config._config import _Config
from taipy.config.checker._checkers._config_checker import _ConfigChecker
from taipy.config.checker.issue_collector import IssueCollector
from taipy.config.common.frequency import Frequency

from ..pipeline_config import PipelineConfig
from ..scenario_config import ScenarioConfig


class _ScenarioConfigChecker(_ConfigChecker):
    def __init__(self, config: _Config, collector: IssueCollector):
        super().__init__(config, collector)

    def _check(self) -> IssueCollector:
        scenario_configs = self._config._sections[ScenarioConfig.name]
        for scenario_config_id, scenario_config in scenario_configs.items():
            if scenario_config_id != _Config.DEFAULT_KEY:
                self._check_if_entity_property_key_used_is_predefined(scenario_config)
                self._check_existing_config_id(scenario_config)
                self._check_frequency(scenario_config_id, scenario_config)
                self._check_pipelines(scenario_config_id, scenario_config)
                self._check_comparators(scenario_config_id, scenario_config)
        return self._collector

    def _check_pipelines(self, scenario_config_id: str, scenario_config: ScenarioConfig):
        self._check_children(
            ScenarioConfig,
            scenario_config_id,
            scenario_config._PIPELINE_KEY,
            scenario_config.pipeline_configs,
            PipelineConfig,
        )

    def _check_frequency(self, scenario_config_id: str, scenario_config: ScenarioConfig):
        if scenario_config.frequency and not isinstance(scenario_config.frequency, Frequency):
            self._error(
                scenario_config._FREQUENCY_KEY,
                scenario_config.frequency,
                f"{scenario_config._FREQUENCY_KEY} field of ScenarioConfig `{scenario_config_id}` must be"
                f" populated with a Frequency value.",
            )

    def _check_comparators(self, scenario_config_id: str, scenario_config: ScenarioConfig):
        if scenario_config.comparators is not None and not isinstance(scenario_config.comparators, dict):
            self._error(
                ScenarioConfig._COMPARATOR_KEY,
                scenario_config.comparators,
                f"{ScenarioConfig._COMPARATOR_KEY} field of ScenarioConfig"
                f" `{scenario_config_id}` must be populated with a dictionary value.",
            )
        else:
            for data_node_id, comparator in scenario_config.comparators.items():
                if data_node_id not in Config.data_nodes:
                    self._error(
                        ScenarioConfig._COMPARATOR_KEY,
                        scenario_config.comparators,
                        f"The key `{data_node_id}` in {ScenarioConfig._COMPARATOR_KEY} field of ScenarioConfig"
                        f" `{scenario_config_id}` must be populated with a valid data node configuration id.",
                    )
                if not callable(comparator):
                    if not isinstance(comparator, list) or not all(callable(comp) for comp in comparator):
                        self._error(
                            ScenarioConfig._COMPARATOR_KEY,
                            scenario_config.comparators,
                            f"The value of `{data_node_id}` in {ScenarioConfig._COMPARATOR_KEY} field of ScenarioConfig"
                            f" `{scenario_config_id}` must be populated with a list of Callable values.",
                        )
