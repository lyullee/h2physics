"""Callback seals distinguish actual definition changes from Python runtime state."""

import sys

import pytest

from h2physics.adapters.facility_consequence import _evaluator_binding


def test_execution_and_string_interning_preserve_callback_binding():
    namespace = {}
    exec(compile("def callback():\n    return 'value with spaces for interning'\n",
                 "authored_callback.py", "exec"), namespace)
    callback = namespace["callback"]
    before = _evaluator_binding(callback)
    for _ in range(1000):
        assert callback() == "value with spaces for interning"
    sys.intern(callback.__code__.co_consts[1])
    assert _evaluator_binding(callback) == before


def test_changed_constant_invalidates_callback_binding():
    def callback():
        return 101

    before = _evaluator_binding(callback)
    callback.__code__ = callback.__code__.replace(co_consts=(None, 102))
    assert callback() == 102
    assert _evaluator_binding(callback) != before


def test_changed_nested_code_invalidates_callback_binding():
    def callback():
        return lambda: 101

    before = _evaluator_binding(callback)
    nested = callback.__code__.co_consts[1].replace(co_consts=(None, 102))
    callback.__code__ = callback.__code__.replace(co_consts=(None, nested))
    assert callback()() == 102
    assert _evaluator_binding(callback) != before


def test_changed_captured_configuration_invalidates_callback_binding():
    configuration = [101]

    def callback():
        return configuration[0]

    before = _evaluator_binding(callback)
    configuration[0] = 102
    assert _evaluator_binding(callback) != before


def test_captured_class_wrapper_is_stable_but_configuration_change_is_detected():
    class Configuration:
        scale = 101

    def callback():
        return Configuration.scale

    before = _evaluator_binding(callback)
    assert callback() == 101
    assert _evaluator_binding(callback) == before
    Configuration.scale = 102
    assert _evaluator_binding(callback) != before


@pytest.mark.parametrize("kind", ("method", "static", "class"))
def test_captured_class_method_code_change_is_detected(kind):
    class Configuration:
        def method(self):
            return 101

        @staticmethod
        def static():
            return 101

        @classmethod
        def class_method(cls):
            return 101

    def callback():
        return Configuration

    before = _evaluator_binding(callback)
    assert _evaluator_binding(callback) == before
    function = vars(Configuration)[{"method": "method", "static": "static",
                                    "class": "class_method"}[kind]]
    if kind != "method":
        function = function.__func__
    function.__code__ = function.__code__.replace(co_consts=(None, 102))
    assert _evaluator_binding(callback) != before
