import time
from concurrent.futures import ThreadPoolExecutor, as_completed,ProcessPoolExecutor
import asyncio

def do_work(task_id:int,duration:float=0.1)->str:
    time.sleep(duration)
    return f"Task {task_id} completed"


def do_cpu_work(task_id:int,iterations:int=1000000)->str:
    res=0
    for i in range(iterations):
        res+=i*i
    return f"Task {task_id} completed (result: {res})"
# def run_sync(tasks:int=5)->list[str]:
#     results:list[str]=[]
    
#     for i in range(tasks):
#         result=do_work(i,duration=0.1)
#         results.append(result)
#     return results

def run_threading(tasks:int=5,max_workers:int =5)->list[str]:
    results:list[str]=[]
    
    with ThreadPoolExecutor(max_workers=max_workers) as executors:
        futures=[executors.submit(do_work,i,0.1) for i in range(tasks)]
        for future in as_completed(futures):
            res=future.result()
            results.append(res)
    return results

def run_multiprocessing(tasks: int = 5, max_workers: int = 5) -> list[str]:
    results: list[str] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(do_cpu_work, i, 1_000_000) for i in range(tasks)]
        for f in as_completed(futures):
            results.append(f.result())        # ← .result() added
    return results     

async def do_async_work(task_id:int,duration:float=0.1)->str:
    await asyncio.sleep(duration)
    return f"Task {task_id} completed"

async def run_asyncio(tasks:int=5)->list[str]:
    task_list=[do_async_work(i,0.1) for i in range(tasks)]
    results=await asyncio.gather(*task_list)
    return list(results)

if __name__=='__main__':
    # start_time=time.perf_counter()
    # results=run_threading(tasks=5)
    # elapsed_time=time.perf_counter()-start_time
    
    # print("Synchronous Results:")
    
    # for res in results:
    #     print(f" {res}")
    
    # print(f"\n Total time: {elapsed_time:.2f} seconds")
    # print("Note: Tasks ran one after another (synchronous execution)")   
    
    #Threading is good for IO bound task->It releases GIL
    #Thread pool executor is good for managing threads
    
    #Multiprocessing for CPU bound task and threading for IO bound task
    
    
    # start_time=time.perf_counter()
    # results=run_multiprocessing(tasks=5,max_workers=5)
    # elapsed_time=time.perf_counter()-start_time
    
    # print("Multiprocessing Results:")
    
    # for res in results:
    #     print(f" {res}")
    
    # print(f"\n Total time: {elapsed_time:.2f} seconds")
    # print("Note: Tasks ran concurrently using threads (I/O bound tasks)")  
    
    #asyncio -> single thread with event loop, doesn't have issue of creating and managuing threads
    
    start_time=time.perf_counter()
    results=asyncio.run(run_asyncio(tasks=5))
    elapsed_time=time.perf_counter()-start_time
    
    print("Asyncio Results")
    for res in results:
        print(f"{res}")
    
    print(f"\nTotal time: {elapsed_time:.2f} seconds")
    print("Note: Tasks ran concurrently using asyncio (modern I/O bound)")