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
from datetime import datetime, timedelta
from time import sleep
from unittest import mock

import pytest

import src.taipy.core as tp
from src.taipy.core._orchestrator._orchestrator_factory import _OrchestratorFactory
from src.taipy.core.config.job_config import JobConfig
from src.taipy.core.data._data_manager import _DataManager
from src.taipy.core.data._filter import _FilterDataNode
from src.taipy.core.data.data_node import DataNode
from src.taipy.core.data.data_node_id import DataNodeId
from src.taipy.core.data.in_memory import InMemoryDataNode
from src.taipy.core.data.operator import JoinOperator, Operator
from src.taipy.core.exceptions.exceptions import NoData
from src.taipy.core.job.job_id import JobId
from taipy.config import Config
from taipy.config.common.scope import Scope
from taipy.config.exceptions.exceptions import InvalidConfigurationId


class FakeDataNode(InMemoryDataNode):
    read_has_been_called = 0
    write_has_been_called = 0

    def __init__(self, config_id, **kwargs):
        scope = kwargs.pop("scope", Scope.SCENARIO)
        super().__init__(config_id=config_id, scope=scope, **kwargs)

    def _read(self, query=None):
        self.read_has_been_called += 1

    def _write(self, data):
        self.write_has_been_called += 1

    @classmethod
    def storage_type(cls) -> str:
        return "fake_inmemory"

    write = DataNode.write  # Make sure that the writing behavior comes from DataNode


class FakeDataframeDataNode(DataNode):
    COLUMN_NAME_1 = "a"
    COLUMN_NAME_2 = "b"

    def __init__(self, config_id, default_data_frame, **kwargs):
        super().__init__(config_id, **kwargs)
        self.data = default_data_frame

    def _read(self):
        return self.data

    @classmethod
    def storage_type(cls) -> str:
        return "fake_df_dn"


class FakeListDataNode(DataNode):
    class Row:
        def __init__(self, value):
            self.value = value

    def __init__(self, config_id, **kwargs):
        super().__init__(config_id, **kwargs)
        self.data = [self.Row(i) for i in range(10)]

    def _read(self):
        return self.data

    @classmethod
    def storage_type(cls) -> str:
        return "fake_list_dn"


def funct_a_b(input: str):
    print("task_a_b")
    return "B"


def funct_b_c(input: str):
    print("task_b_c")
    return "C"


def funct_b_d(input: str):
    print("task_b_d")
    return "D"


class TestDataNode:
    def test_create_with_default_values(self):
        dn = DataNode("foo_bar")
        assert dn.config_id == "foo_bar"
        assert dn.scope == Scope.SCENARIO
        assert dn.id is not None
        assert dn.name is None
        assert dn.owner_id is None
        assert dn.parent_ids == set()
        assert dn.last_edition_date is None
        assert dn.job_ids == []
        assert not dn.is_ready_for_reading
        assert len(dn.properties) == 0

    def test_create(self):
        a_date = datetime.now()
        dn = DataNode(
            "foo_bar",
            Scope.SCENARIO,
            DataNodeId("an_id"),
            "a name",
            "a_scenario_id",
            {"a_parent_id"},
            a_date,
            [dict(job_id="a_job_id")],
            edit_in_progress=False,
            prop="erty",
        )
        assert dn.config_id == "foo_bar"
        assert dn.scope == Scope.SCENARIO
        assert dn.id == "an_id"
        assert dn.name == "a name"
        assert dn.owner_id == "a_scenario_id"
        assert dn.parent_ids == {"a_parent_id"}
        assert dn.last_edition_date == a_date
        assert dn.job_ids == ["a_job_id"]
        assert dn.is_ready_for_reading
        assert len(dn.properties) == 1
        assert dn.properties["prop"] == "erty"

        with pytest.raises(InvalidConfigurationId):
            DataNode("foo bar")

    def test_read_write(self):
        dn = FakeDataNode("foo_bar")
        with pytest.raises(NoData):
            assert dn.read() is None
            dn.read_or_raise()
        assert dn.write_has_been_called == 0
        assert dn.read_has_been_called == 0
        assert not dn.is_ready_for_reading
        assert dn.last_edition_date is None
        assert dn.job_ids == []
        assert dn.edits == []

        dn.write("Any data")
        assert dn.write_has_been_called == 1
        assert dn.read_has_been_called == 0
        assert dn.last_edition_date is not None
        first_edition = dn.last_edition_date
        assert dn.is_ready_for_reading
        assert dn.job_ids == []
        assert len(dn.edits) == 1
        assert dn.get_last_edit()["timestamp"] == dn.last_edit_date

        sleep(0.1)

        dn.write("Any other data", job_id := JobId("a_job_id"))
        assert dn.write_has_been_called == 2
        assert dn.read_has_been_called == 0
        second_edition = dn.last_edition_date
        assert first_edition < second_edition
        assert dn.is_ready_for_reading
        assert dn.job_ids == [job_id]
        assert len(dn.edits) == 2
        assert dn.get_last_edit()["timestamp"] == dn.last_edit_date

        dn.read()
        assert dn.write_has_been_called == 2
        assert dn.read_has_been_called == 1
        second_edition = dn.last_edition_date
        assert first_edition < second_edition
        assert dn.is_ready_for_reading
        assert dn.job_ids == [job_id]

    def test_ready_for_reading(self):
        dn = InMemoryDataNode("foo_bar", Scope.CYCLE)
        assert dn.last_edit_date is None
        assert not dn.is_ready_for_reading
        assert dn.job_ids == []

        dn.lock_edit()
        assert dn.last_edit_date is None
        assert not dn.is_ready_for_reading
        assert dn.job_ids == []

        dn.unlock_edit(datetime.now(), JobId("a_job_id"))
        assert dn.last_edit_date is None
        assert not dn.is_ready_for_reading
        assert dn.job_ids == []

        dn.lock_edit()
        assert dn.last_edit_date is None
        assert not dn.is_ready_for_reading
        assert dn.job_ids == []

        dn.write("toto", job_id := JobId("a_job_id"))
        assert dn.last_edit_date is not None
        assert dn.is_ready_for_reading
        assert dn.job_ids == [job_id]

    def test_is_up_to_date_no_validity_period(self):
        # Test Never been writen
        dn = InMemoryDataNode("foo", Scope.SCENARIO, DataNodeId("id"), "name", "owner_id")
        assert not dn.is_up_to_date

        # test has been writen
        dn.write("My data")
        assert dn.is_up_to_date

    def test_is_up_to_date_with_30_min_validity_period(self):
        # Test Never been writen
        dn = InMemoryDataNode(
            "foo", Scope.SCENARIO, DataNodeId("id"), "name", "owner_id", validity_period=timedelta(minutes=30)
        )
        assert dn.is_up_to_date is False

        # Has been writen less than 30 minutes ago
        dn.write("My data")
        assert dn.is_up_to_date is True

        # Has been writen more than 30 minutes ago
        dn.last_edit_date = datetime.now() + timedelta(days=-1)
        assert dn.is_up_to_date is False

    def test_is_up_to_date_with_5_days_validity_period(self):
        # Test Never been writen
        dn = InMemoryDataNode("foo", Scope.SCENARIO, validity_period=timedelta(days=5))
        assert dn.is_up_to_date is False

        # Has been writen less than 30 minutes ago
        dn.write("My data")
        assert dn.is_up_to_date is True

        # Has been writen more than 30 minutes ago
        dn._last_edit_date = datetime.now() - timedelta(days=6)
        _DataManager()._set(dn)
        assert dn.is_up_to_date is False

    def test_do_not_recompute_data_node_up_to_date_but_continue_pipeline_execution(self):
        Config.configure_job_executions(mode=JobConfig._DEVELOPMENT_MODE)

        a = Config.configure_data_node("A", "pickle", default_data="A")
        b = Config.configure_data_node("B", "pickle")
        c = Config.configure_data_node("C", "pickle")
        d = Config.configure_data_node("D", "pickle")

        task_a_b = Config.configure_task("task_a_b", funct_a_b, input=a, output=b, skippable=True)
        task_b_c = Config.configure_task("task_b_c", funct_b_c, input=b, output=c)
        task_b_d = Config.configure_task("task_b_d", funct_b_d, input=b, output=d)
        pipeline_c = Config.configure_pipeline("pipeline_c", [task_a_b, task_b_c])
        pipeline_d = Config.configure_pipeline("pipeline_d", [task_a_b, task_b_d])
        scenario_cfg = Config.configure_scenario("scenario", [pipeline_c, pipeline_d])

        _OrchestratorFactory._build_dispatcher()

        scenario = tp.create_scenario(scenario_cfg)
        scenario.submit()
        assert scenario.A.read() == "A"
        assert scenario.B.read() == "B"
        assert scenario.C.read() == "C"
        assert scenario.D.read() == "D"

        assert len(tp.get_jobs()) == 4
        jobs_and_status = [(job.task.config_id, job.status) for job in tp.get_jobs()]
        assert ("task_a_b", tp.Status.COMPLETED) in jobs_and_status
        assert ("task_a_b", tp.Status.SKIPPED) in jobs_and_status
        assert ("task_b_c", tp.Status.COMPLETED) in jobs_and_status
        assert ("task_b_d", tp.Status.COMPLETED) in jobs_and_status

    def test_pandas_filter(self, default_data_frame):
        df_dn = FakeDataframeDataNode("fake_dataframe_dn", default_data_frame)
        COLUMN_NAME_1 = "a"
        COLUMN_NAME_2 = "b"
        assert isinstance(df_dn[COLUMN_NAME_1], _FilterDataNode)
        assert isinstance(df_dn[[COLUMN_NAME_1, COLUMN_NAME_2]], _FilterDataNode)

    def test_filter(self, default_data_frame):
        dn = FakeDataNode("fake_dn")
        dn.write("Any data")

        assert NotImplementedError == dn.filter((("any", 0, Operator.EQUAL)), JoinOperator.OR)
        assert NotImplementedError == dn.filter((("any", 0, Operator.NOT_EQUAL)), JoinOperator.OR)
        assert NotImplementedError == dn.filter((("any", 0, Operator.LESS_THAN)), JoinOperator.AND)
        assert NotImplementedError == dn.filter((("any", 0, Operator.LESS_OR_EQUAL)), JoinOperator.AND)
        assert NotImplementedError == dn.filter((("any", 0, Operator.GREATER_THAN)))
        assert NotImplementedError == dn.filter(("any", 0, Operator.GREATER_OR_EQUAL))

        df_dn = FakeDataframeDataNode("fake_dataframe_dn", default_data_frame)

        COLUMN_NAME_1 = "a"
        COLUMN_NAME_2 = "b"
        assert len(df_dn.filter((COLUMN_NAME_1, 1, Operator.EQUAL))) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] == 1]
        )
        assert len(df_dn.filter((COLUMN_NAME_1, 1, Operator.NOT_EQUAL))) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] != 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, 1, Operator.EQUAL)])) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] == 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, 1, Operator.NOT_EQUAL)])) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] != 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, 1, Operator.LESS_THAN)])) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] < 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, 1, Operator.LESS_OR_EQUAL)])) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] <= 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, 1, Operator.GREATER_THAN)])) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] > 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, 1, Operator.GREATER_OR_EQUAL)])) == len(
            default_data_frame[default_data_frame[COLUMN_NAME_1] >= 1]
        )
        assert len(df_dn.filter([(COLUMN_NAME_1, -1000, Operator.LESS_OR_EQUAL)])) == 0
        assert len(df_dn.filter([(COLUMN_NAME_1, 1000, Operator.GREATER_OR_EQUAL)])) == 0
        assert len(df_dn.filter([(COLUMN_NAME_1, 4, Operator.EQUAL), (COLUMN_NAME_1, 5, Operator.EQUAL)])) == len(
            default_data_frame[(default_data_frame[COLUMN_NAME_1] == 4) & (default_data_frame[COLUMN_NAME_1] == 5)]
        )
        assert len(
            df_dn.filter([(COLUMN_NAME_1, 4, Operator.EQUAL), (COLUMN_NAME_2, 5, Operator.EQUAL)], JoinOperator.OR)
        ) == len(
            default_data_frame[(default_data_frame[COLUMN_NAME_1] == 4) | (default_data_frame[COLUMN_NAME_2] == 5)]
        )
        assert len(
            df_dn.filter(
                [(COLUMN_NAME_1, 1, Operator.GREATER_THAN), (COLUMN_NAME_2, 3, Operator.GREATER_THAN)], JoinOperator.AND
            )
        ) == len(default_data_frame[(default_data_frame[COLUMN_NAME_1] > 1) & (default_data_frame[COLUMN_NAME_2] > 3)])
        assert len(
            df_dn.filter(
                [(COLUMN_NAME_1, 2, Operator.GREATER_THAN), (COLUMN_NAME_1, 3, Operator.GREATER_THAN)], JoinOperator.OR
            )
        ) == len(default_data_frame[(default_data_frame[COLUMN_NAME_1] > 2) | (default_data_frame[COLUMN_NAME_1] > 3)])
        assert len(
            df_dn.filter(
                [(COLUMN_NAME_1, 10, Operator.GREATER_THAN), (COLUMN_NAME_1, -10, Operator.LESS_THAN)], JoinOperator.AND
            )
        ) == len(
            default_data_frame[(default_data_frame[COLUMN_NAME_1] > 10) | (default_data_frame[COLUMN_NAME_1] < -10)]
        )
        assert len(
            df_dn.filter(
                [(COLUMN_NAME_1, 10, Operator.GREATER_THAN), (COLUMN_NAME_1, -10, Operator.LESS_THAN)], JoinOperator.OR
            )
        ) == len(
            default_data_frame[(default_data_frame[COLUMN_NAME_1] > 10) | (default_data_frame[COLUMN_NAME_1] < -10)]
        )
        list_dn = FakeListDataNode("fake_list_dn")

        KEY_NAME = "value"

        assert len(list_dn.filter((KEY_NAME, 4, Operator.EQUAL))) == 1
        assert len(list_dn.filter((KEY_NAME, 4, Operator.NOT_EQUAL))) == 9
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.EQUAL)])) == 1
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.NOT_EQUAL)])) == 9
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.LESS_THAN)])) == 4
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.LESS_OR_EQUAL)])) == 5
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.GREATER_THAN)])) == 5
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.GREATER_OR_EQUAL)])) == 6
        assert len(list_dn.filter([(KEY_NAME, -1000, Operator.LESS_OR_EQUAL)])) == 0
        assert len(list_dn.filter([(KEY_NAME, 1000, Operator.GREATER_OR_EQUAL)])) == 0

        assert len(list_dn.filter([(KEY_NAME, 4, Operator.EQUAL), (KEY_NAME, 5, Operator.EQUAL)])) == 0
        assert len(list_dn.filter([(KEY_NAME, 4, Operator.EQUAL), (KEY_NAME, 5, Operator.EQUAL)], JoinOperator.OR)) == 2
        assert (
            len(list_dn.filter([(KEY_NAME, 4, Operator.EQUAL), (KEY_NAME, 11, Operator.EQUAL)], JoinOperator.AND)) == 0
        )
        assert (
            len(list_dn.filter([(KEY_NAME, 4, Operator.EQUAL), (KEY_NAME, 11, Operator.EQUAL)], JoinOperator.OR)) == 1
        )

        assert (
            len(list_dn.filter([(KEY_NAME, -10, Operator.LESS_OR_EQUAL), (KEY_NAME, 11, Operator.GREATER_OR_EQUAL)]))
            == 0
        )
        assert (
            len(
                list_dn.filter(
                    [
                        (KEY_NAME, 4, Operator.GREATER_OR_EQUAL),
                        (KEY_NAME, 6, Operator.GREATER_OR_EQUAL),
                    ],
                    JoinOperator.AND,
                )
            )
            == 4
        )
        assert (
            len(
                list_dn.filter(
                    [
                        (KEY_NAME, 4, Operator.GREATER_OR_EQUAL),
                        (KEY_NAME, 6, Operator.GREATER_OR_EQUAL),
                        (KEY_NAME, 11, Operator.EQUAL),
                    ],
                    JoinOperator.AND,
                )
            )
            == 0
        )
        assert (
            len(
                list_dn.filter(
                    [
                        (KEY_NAME, 4, Operator.GREATER_OR_EQUAL),
                        (KEY_NAME, 6, Operator.GREATER_OR_EQUAL),
                        (KEY_NAME, 11, Operator.EQUAL),
                    ],
                    JoinOperator.OR,
                )
            )
            == 6
        )

    def test_data_node_update_after_writing(self):
        dn = FakeDataNode("foo")

        _DataManager._set(dn)
        assert not _DataManager._get(dn.id).is_ready_for_reading
        dn.write("Any data")

        assert dn.is_ready_for_reading
        assert _DataManager._get(dn.id).is_ready_for_reading

    def test_expiration_date_raise_if_never_write(self):
        dn = FakeDataNode("foo")

        with pytest.raises(NoData):
            dn.expiration_date

    def test_validity_null_if_never_write(self):
        dn = FakeDataNode("foo")

        assert dn.validity_period is None

    def test_auto_set_and_reload(self, current_datetime):
        dn_1 = InMemoryDataNode(
            "foo",
            scope=Scope.GLOBAL,
            id=DataNodeId("an_id"),
            name="foo",
            owner_id=None,
            parent_ids=None,
            last_edit_date=current_datetime,
            edits=[dict(job_id="a_job_id")],
            edit_in_progress=False,
            validity_period=None,
        )

        dm = _DataManager()
        dm._set(dn_1)

        dn_2 = dm._get(dn_1)

        # auto set & reload on scope attribute
        assert dn_1.scope == Scope.GLOBAL
        assert dn_2.scope == Scope.GLOBAL
        dn_1.scope = Scope.CYCLE
        assert dn_1.scope == Scope.CYCLE
        assert dn_2.scope == Scope.CYCLE
        dn_2.scope = Scope.SCENARIO
        assert dn_1.scope == Scope.SCENARIO
        assert dn_2.scope == Scope.SCENARIO

        new_datetime = current_datetime + timedelta(1)
        new_datetime_1 = current_datetime + timedelta(3)

        # auto set & reload on last_edition_date attribute
        assert dn_1.last_edition_date == current_datetime
        assert dn_2.last_edition_date == current_datetime
        dn_1.last_edition_date = new_datetime_1
        assert dn_1.last_edition_date == new_datetime_1
        assert dn_2.last_edition_date == new_datetime_1
        dn_2.last_edition_date = new_datetime
        assert dn_1.last_edition_date == new_datetime
        assert dn_2.last_edition_date == new_datetime

        # auto set & reload on name attribute
        assert dn_1.name == "foo"
        assert dn_2.name == "foo"
        dn_1.name = "fed"
        assert dn_1.name == "fed"
        assert dn_2.name == "fed"
        dn_2.name = "def"
        assert dn_1.name == "def"
        assert dn_2.name == "def"

        # auto set & reload on parent_ids attribute (set() object does not have auto set yet)
        assert dn_1.parent_ids == set()
        assert dn_2.parent_ids == set()
        dn_1._parent_ids.update(["sc2"])
        _DataManager._set(dn_1)
        assert dn_1.parent_ids == {"sc2"}
        assert dn_2.parent_ids == {"sc2"}
        dn_2._parent_ids.clear()
        dn_2._parent_ids.update(["sc1"])
        _DataManager._set(dn_2)
        assert dn_1.parent_ids == {"sc1"}
        assert dn_2.parent_ids == {"sc1"}

        # auto set & reload on edition_in_progress attribute
        assert not dn_2.edition_in_progress
        assert not dn_1.edition_in_progress
        dn_1.edition_in_progress = True
        assert dn_1.edition_in_progress
        assert dn_2.edition_in_progress
        dn_2.unlock_edition()
        assert not dn_1.edition_in_progress
        assert not dn_2.edition_in_progress
        dn_1.lock_edition()
        assert dn_1.edition_in_progress
        assert dn_2.edition_in_progress

        # auto set & reload on validity_period attribute
        time_period_1 = timedelta(1)
        time_period_2 = timedelta(5)
        assert dn_1.validity_period is None
        assert dn_2.validity_period is None
        dn_1.validity_period = time_period_1
        assert dn_1.validity_period == time_period_1
        assert dn_2.validity_period == time_period_1
        dn_2.validity_period = time_period_2
        assert dn_1.validity_period == time_period_2
        assert dn_2.validity_period == time_period_2

        # auto set & reload on properties attribute
        assert dn_1.properties == {}
        assert dn_2.properties == {}
        dn_1._properties["qux"] = 4
        assert dn_1.properties["qux"] == 4
        assert dn_2.properties["qux"] == 4

        assert dn_1.properties == {"qux": 4}
        assert dn_2.properties == {"qux": 4}
        dn_2._properties["qux"] = 5
        assert dn_1.properties["qux"] == 5
        assert dn_2.properties["qux"] == 5

        dn_1.last_edition_date = new_datetime

        assert len(dn_1.job_ids) == 1
        assert len(dn_2.job_ids) == 1

        with dn_1 as dn:
            assert dn.config_id == "foo"
            assert dn.owner_id is None
            assert dn.scope == Scope.SCENARIO
            assert dn.last_edition_date == new_datetime
            assert dn.name == "def"
            assert dn.edition_in_progress
            assert dn.validity_period == time_period_2
            assert len(dn.job_ids) == 1
            assert dn._is_in_context
            assert dn.properties["qux"] == 5

            new_datetime_2 = new_datetime + timedelta(5)

            dn.scope = Scope.CYCLE
            dn.last_edition_date = new_datetime_2
            dn.name = "abc"
            dn.edition_in_progress = False
            dn.validity_period = None
            dn.properties["qux"] = 9

            assert dn.config_id == "foo"
            assert dn.owner_id is None
            assert dn.scope == Scope.SCENARIO
            assert dn.last_edition_date == new_datetime
            assert dn.name == "def"
            assert dn.edition_in_progress
            assert dn.validity_period == time_period_2
            assert len(dn.job_ids) == 1
            assert dn.properties["qux"] == 5

        assert dn_1.config_id == "foo"
        assert dn_1.owner_id is None
        assert dn_1.scope == Scope.CYCLE
        assert dn_1.last_edition_date == new_datetime_2
        assert dn_1.name == "abc"
        assert not dn_1.edition_in_progress
        assert dn_1.validity_period is None
        assert not dn_1._is_in_context
        assert len(dn_1.job_ids) == 1
        assert dn_1.properties["qux"] == 9

    def test_get_parents(self, data_node):
        with mock.patch("src.taipy.core.get_parents") as mck:
            data_node.get_parents()
            mck.assert_called_once_with(data_node)

    def test_unlock_edition_deprecated(self):
        dn = FakeDataNode("foo")

        with pytest.warns(DeprecationWarning):
            with mock.patch("src.taipy.core.data.data_node.DataNode.unlock_edit") as unlock_edit:
                dn.unlock_edition(datetime.now(), None)
                unlock_edit.assert_called_once_with()

    def test_lock_edition_deprecated(self):
        dn = FakeDataNode("foo")

        with pytest.warns(DeprecationWarning):
            with mock.patch("src.taipy.core.data.data_node.DataNode.lock_edit") as lock_edit:
                dn.lock_edition()
                lock_edit.assert_called_once()

    def test_edition_in_progress_deprecated(self):
        dn = FakeDataNode("foo")

        with pytest.warns(DeprecationWarning):
            dn.edition_in_progress

        assert dn.edit_in_progress == dn.edition_in_progress
        dn.edition_in_progress = True
        assert dn.edit_in_progress == dn.edition_in_progress

    def test_last_edition_date_deprecated(self):
        dn = FakeDataNode("foo")

        with pytest.warns(DeprecationWarning):
            dn.last_edition_date

        assert dn.last_edit_date == dn.last_edition_date
        dn.last_edition_date = datetime.now()
        assert dn.last_edit_date == dn.last_edition_date

    def test_parent_id_deprecated(self):
        dn = FakeDataNode("foo", owner_id="owner_id")

        with pytest.warns(DeprecationWarning):
            dn.parent_id

        assert dn.owner_id == dn.parent_id
        with pytest.warns(DeprecationWarning):
            dn.parent_id = "owner_id_2"

        assert dn.owner_id == dn.parent_id
        assert dn.owner_id == "owner_id_2"

    def test_cacheable_deprecated_false(self):
        dn = FakeDataNode("foo")
        with pytest.warns(DeprecationWarning):
            dn.cacheable
        assert dn.cacheable is False

    def test_cacheable_deprecated_true(self):
        dn = FakeDataNode("foo", properties={"cacheable": True})
        with pytest.warns(DeprecationWarning):
            dn.cacheable
        assert dn.cacheable is True

    def test_data_node_with_env_variable_value_not_stored(self):
        dn_config = Config.configure_data_node("A", prop="ENV[FOO]")
        with mock.patch.dict(os.environ, {"FOO": "bar"}):
            dn = _DataManager._bulk_get_or_create([dn_config])[dn_config]
            assert dn._properties.data["prop"] == "ENV[FOO]"
            assert dn.properties["prop"] == "bar"
            assert dn.prop == "bar"

    def test_path_populated_with_config_default_path(self):
        dn_config = Config.configure_data_node("data_node", "pickle", default_path="foo.p")
        assert dn_config.default_path == "foo.p"
        data_node = _DataManager._bulk_get_or_create([dn_config])[dn_config]
        assert data_node.path == "foo.p"
        data_node.path = "baz.p"
        assert data_node.path == "baz.p"

    def test_track_edit(self):
        dn_config = Config.configure_data_node("A")
        data_node = _DataManager._bulk_get_or_create([dn_config])[dn_config]

        data_node.write(data="1", job_id="job_1")
        data_node.write(data="2", job_id="job_1")
        data_node.write(data="3", job_id="job_1")

        assert len(data_node.edits) == 3
        assert len(data_node.job_ids) == 3
        assert data_node.edits[-1] == data_node.get_last_edit()
        assert data_node.last_edit_date == data_node.get_last_edit().get("timestamp")

        date = datetime(2050, 1, 1, 12, 12)
        data_node.write(data="4", timestamp=date, message="This is a comment on this edit", env="staging")

        assert len(data_node.edits) == 4
        assert len(data_node.job_ids) == 3
        assert data_node.edits[-1] == data_node.get_last_edit()

        last_edit = data_node.get_last_edit()
        assert last_edit["message"] == "This is a comment on this edit"
        assert last_edit["env"] == "staging"
        assert last_edit["timestamp"] == date

    def test_label(self):
        a_date = datetime.now()
        dn = DataNode(
            "foo_bar",
            Scope.SCENARIO,
            DataNodeId("an_id"),
            "a name",
            "a_scenario_id",
            {"a_parent_id"},
            a_date,
            [dict(job_id="a_job_id")],
            edit_in_progress=False,
            prop="erty",
        )
        with mock.patch("src.taipy.core.get") as get_mck:

            class MockOwner:
                label = "owner_label"

                def get_label(self):
                    return self.label

            get_mck.return_value = MockOwner()
            assert dn.get_label() == "owner_label > " + dn.name
            assert dn.get_simple_label() == dn.name

    def test_explicit_label(self):
        a_date = datetime.now()
        dn = DataNode(
            "foo_bar",
            Scope.SCENARIO,
            DataNodeId("an_id"),
            "a name",
            "a_scenario_id",
            {"a_parent_id"},
            a_date,
            [dict(job_id="a_job_id")],
            edit_in_progress=False,
            label="a label",
        )
        assert dn.get_label() == "a label"
        assert dn.get_simple_label() == "a label"
