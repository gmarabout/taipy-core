# Copyright 2022 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from typing import Optional

from ._cycle_model import _CycleModel
from ._cycle_repository import _CycleRepository


class _CycleSQLRepository(_CycleRepository):
    def __init__(self):
        super().__init__(model=_CycleModel, model_name="cycle")

    def _get_by_config_and_parent_id(self, config_id: str, parent_id: Optional[str]):
        return super().repository._get_by_config_and_parent_id(config_id, parent_id)

    def _get_by_configs_and_parent_ids(self, configs_and_parent_ids):
        return super().repository._get_by_configs_and_parent_ids(configs_and_parent_ids)