import pytest

from src.utils.stack_info import get_is_stack_deployed, get_stack_output_value

_STACK_DEPLOYED = get_is_stack_deployed()


@pytest.mark.skipif(_STACK_DEPLOYED is False, reason="AWS Stack is deployed")
def test_get_deployed_stack_valid_output():
    val = get_stack_output_value("NAIPTileApi")
    assert val


@pytest.mark.skipif(_STACK_DEPLOYED is False, reason="AWS Stack is deployed")
def test_get_deployed_stack_invalid_output():
    try:
        get_stack_output_value("XXXX")
        raise AssertionError
    except Exception as e:
        assert isinstance(e, KeyError)


@pytest.mark.skipif(_STACK_DEPLOYED is True, reason="AWS Stack is not deployed")
def test_get_undeployed_stack_output():
    try:
        get_stack_output_value("XXXX")
        raise AssertionError
    except Exception as e:
        assert isinstance(e, ValueError)
