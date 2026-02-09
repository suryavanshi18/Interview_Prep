import random
import time
from functools import wraps
'''
args is list of tuple
kwargs is list of dictionary
to unpack tuple we user *
to unpack dict we use **
'''
def retry(n_retries, wait, exception):
    def main_retry(f):
        @wraps(f)  # <-- add this
        def new_fn(*args, **kwargs):
            i = 0
            while i < n_retries:
                try:
                    return f(*args, **kwargs)
                except tuple(exception) as e:
                    print(f'{f.__name__} failed. Retrying...[{i}/{n_retries}]')
                    i += 1
                    if i == n_retries:
                        raise e
                    time.sleep(wait)
        return new_fn
    return main_retry

class NetworkError(Exception):
    pass

class UserNotFoundException(Exception):
    pass

@retry(n_retries=5, wait=1, exception=[NetworkError])
def get_user_info(user_id: int):
    print("Calling external service")
    users = {1: "Tom", 2: "Mary", 3: "Kevin"}
    if random.random() < 0.5:
        raise NetworkError("Unreliable internet connection")
    if user_id not in users:
        raise UserNotFoundException("Provided user not in list")
    return users[user_id]

if __name__ == '__main__':
    '''
    t=(1,2,3,4)
    d={"a":1,"b":2}
    print(t)
    print(*t)
    print(d)
    print(**d)
    **d tries to unpack the dict into keyword arguments, like this:
    print(a=1, b=2)
    But print() does not accept arbitrary keyword arguments like a or b.
    **kwargs only works if the function expects keyword arguments with those names.
    def foo(a, b):
        print(a, b)
    foo(**d)
    o/p
    1 2
    '''
    user_id = 1
    name = get_user_info(user_id)
    print(f'Name of {user_id} is {name}')