import time

from enforce_typing import enforce_types


@enforce_types
# pylint: disable=keyword-arg-before-vararg
def retryFunction(f, retries: int = 1, delay=10, *args, **kwargs):
    """
    @description
      Retry a function call if it fails.

    @param
      f -- the function to call
      retries -- the number of times to retry
      *args -- the arguments to pass to the function
      **kwargs -- the keyword arguments to pass to the function

    @return
      The return value of the function call.
    """
    for i in range(retries):
        try:
            return f(*args, **kwargs)
        # pylint: disable=broad-exception-caught
        except Exception as e:
            print(f"retry {i}: {e}")
            time.sleep(delay)
    # pylint: disable=broad-exception-raised
    raise Exception(f"failed after {retries} retries")
