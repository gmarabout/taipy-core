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

from src.taipy.core.job._utils import _migrate_subscriber


def test_migrate_subscriber():
    assert _migrate_subscriber("", "") == ("", "")
    assert _migrate_subscriber("foo.bar", "baz") == ("foo.bar", "baz")
    assert _migrate_subscriber("taipy.core._scheduler._scheduler", "_Scheduler._on_status_change") == (
        "taipy.core._orchestrator._orchestrator",
        "_Orchestrator._on_status_change",
    )
    assert _migrate_subscriber("taipy.core._orchestrator._orchestrator", "_Orchestrator._on_status_change") == (
        "taipy.core._orchestrator._orchestrator",
        "_Orchestrator._on_status_change",
    )
