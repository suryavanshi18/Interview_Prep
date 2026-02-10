from functools import wraps
from typing import Callable,Any
import time

def get_time(func:Callable)->Callable:
    '''
    Get the time of given function
    If we dont write @wraps(func) then it would 
    expensive_funciton would give wrapper information
    Hence for expensive_funciton to behave as normal func
    we add @wraps(func)
    
    Callable datatype means any function which can be callable to other function
    
    Any return type means the function can return any type of data
    
    *args and **kwargs are added to wrapper function so that they
    can take arguments of the expensive_funciton() or function on which wrapper is applied
    '''
    @wraps(func)
    def wrapper(*args,**kwargs)->Any:
        '''
        Wrapper doc string
        '''
        start_time:float=time.perf_counter()
        result:Any=func(*args,**kwargs)
        end_time:float=time.perf_counter()
        print(f"Ran {func.__name__} in {end_time-start_time:.2f} seconds")
        return result
    return wrapper
        
        
        
@get_time
def expensive_funciton()->None:
    time.sleep(2)
    print('Done!')
    
if __name__=='__main__':
    '''
    We will get the information about the wrapper
    if  @wraps is not added to wrapper
    print(expensive_funciton.__annotations__)
    print(expensive_funciton.__name__)
    print(expensive_funciton.__doc__)
    '''
    print(expensive_funciton.__annotations__)
    print(expensive_funciton.__name__)
    print(expensive_funciton.__doc__)
    expensive_funciton()
    
'''
Max Retries
    Client
    Retry failed request
    Timeouts,network issues

Rate limit
    Server side
    Limit on how many requets you can make
    Server overload
    
    
Max retries = You knock on a door, nobody answers, so you knock again
Rate limiting = The doorman says "Only 5 visitors per hour, come back later

Latency vs Response time
    
    Latency->Time required for request to be handled
            Physical distance data needs to travel in the network + time spent on queuing 
    Response time->total time between sending a req and receiving response 
                   Latency + server's time to generate response 
'''