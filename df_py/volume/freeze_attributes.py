from enforce_typing import enforce_types

@enforce_types
def freeze_attributes(func):
    # makes sure the state is not changed during the function call
    # use as decorator to preserve state.
    # only the constructor and the calculate method should be allowed to change state
    def wrapper(self, *args, **kwargs):
        self._freeze_attributes = True
        return_value = func(self, *args, **kwargs)
        self._freeze_attributes = False
        return return_value

    return wrapper
