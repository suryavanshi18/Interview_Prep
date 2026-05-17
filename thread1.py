import time
from concurrent.futures import ThreadPoolExecutor,as_completed,ProcessPoolExecutor
import asyncio

async def do_async_word(task_id:int,duration:float=0.1)->str:
    await asyncio.sleep(duration)
    return f"Task {task_id} completed"

async def run_asyncio(tasks:int=5)->list[str]:
    task_list=[do_async_word(i,0.1) for i in range(tasks)]
    results=await asyncio.gather(*task_list)
    return list(results)
    
    

def do_something(task_id:int,duration:float=0.1)->str:
    time.sleep(duration)
    return f"Task {task_id} was completed"

def run_sync(tasks:int=5)->list[str]:
    """
        Syncronous execution
        Task run one after another
    """
    
    results:list[str]=[]
    for i in range(tasks):
        result=do_something(i,duration=0.1)
        results.append(result)
    return results

def run_threading(tasks:int=5,max_workers:int =4)->list[str]:
    results:list[str]=[]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures=[executor.submit(do_something,i,0.1) for i in range(tasks)]
        #as_completed function returns results when they are finished
        for fur in as_completed(futures):
            result=fur.result()
            results.append(result)
    return results

def do_cpu(task_id:int,iterations:int=1000000)->str:
    res=0
    for i in range(iterations):
        res+=i*i
    
    return f"Task {task_id} completed (result: {res})"  
    


def run_multiprocessing(tasks:int=5,max_workers:int=5)->list[str]:
    results:list[str]=[]
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures=[executor.submit(do_cpu,i,1000000) for i in range(tasks)]
        for fur in as_completed(futures):
            res=fur.result()
            results.append(res)
    return results
            
        
        
    

if __name__=='__main__':
    start_time=time.perf_counter()
    # results=run_multiprocessing(tasks=5)
    results=asyncio.run(run_asyncio(tasks=5))
    elapsed_time=time.perf_counter()
    
    # print("Synchronous Results:")
    print("Ayncio Results:")
    for res in results:
        print(f" {res}")
        
    print(f"\n Total time: {elapsed_time-start_time:.2f} seconds")
"""
    Threading is good for io bound tasks . When one thread is waiting for IO other threads can work
    GIL makes thread not work in parallel, but when thread is in IO
    then GIL lock is released making other threads to run
    
    MultiProcessing-> Creates seperate process with own memory space and python interpretor. But it has more memory
    ProcessPoolExecutor
    
    Use MultiProcessing for CPU bound tasks and threading for IO bound tasks
    https://www.youtube.com/watch?v=QlkXji08lno&t=45s
    
    Asyncio uses single thread with single event loop
    More efficient for io bound operations
    
    
    Concurrency Model
        Asyncio: Asyncio utilizes a single-threaded event loop to handle concurrency. It is designed to efficiently manage I/O-bound tasks by using asynchronous coroutines and non-blocking operations. This approach avoids the complexity of multi-threading and can handle a large number of simultaneous I/O operations without creating multiple threads.
        
        Threading: Threading allows multiple threads to run concurrently, each executing a portion of the code in parallel. However, in Python, the Global Interpreter Lock (GIL) restricts the execution of Python bytecode to one thread at a time. As a result, while threading enables concurrency, it may not provide significant performance improvements for CPU-bound tasks due to the GIL's limitation. For CPU-bound operations, threading might not achieve true parallelism in CPython.
"""


