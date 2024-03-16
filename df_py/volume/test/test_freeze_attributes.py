from enforce_typing import enforce_types
import pytest

from df_py.pyutil.freeze_attributes import freeze_attributes

class MockClass():

    def set_mock_attribute(self, attr_name, attr_value):
        self._freeze_attributes = False
        setattr(self, attr_name, attr_value)
        self._freeze_attributes = True


@enforce_types
def test_freeze_attributes():
    rc = MockClass()
    rc._freeze_attributes = True

    with pytest.raises(AttributeError):
        rc.new_attr = 1

    rc._freeze_attributes = False
    rc.new_attr = 1
