from threading import Thread,Lock
from time import sleep
#################### v1 ####################
# class Hello:
#     def do(self):
#         for i in range(5):
#             print("Hello",i+1)
# class Hi:
#     def do(self):
#         for i in range(5):
#             print("Hi",i+1)
            
            
##################### v2 ####################

# from threading import Thread
# from time import sleep

# def hello():
#     for i in range(5):
#         print("Hello", i+1)
#         sleep(0.3)

# def hi():
#     for i in range(5):
#         print("Hi", i+1)
#         sleep(0.2)

# if __name__ == '__main__':
#     t1 = Thread(target=hello)
#     t2 = Thread(target=hi)
#     t1.start()
#     t2.start()
#     t1.join()
#     t2.join()


"""
    Threads allow you to run multiple task in parallel on single/multiple cores
    Threads allow you to use shared memory for passing same data
    
    Due to GIL only one thread can run at a time
    For CPU bound task use multiprocessing
"""


# def print_message():
#     for i in range(2):
#         print("Hello from thread!",i+1)
#         sleep(0.3)
        
# def print_message(name,count):
#     for i in range(count):
#         print(f"Hello from {name}!",i+1)
#         sleep(0.3)
        
        


        
# if __name__=='__main__':
    # thread=Thread(target=print_message)
    # thread.start()
    # print("Hello from main thread!")
    
    #we just make one thread finish and then start another thread
    
    # thread=Thread(target=print_message)
    # thread.start()
    # thread.join()
    # print("Hello from main thread!")
    
    #print_message thread will go through its iterations first and then in the end main thread will finish
    
    
    ## Arguments
    # thread=Thread(target=print_message,args=("Thread function",2))
    # thread.start()
    # thread.join()
    # print("Hello from main thread!")
    
    
    #Multithreading
    # threads=[]
    # for i in range(3):
    #     thread=Thread(target=print_message,args=(f"Thread function-{i+1}",2))
    #     threads.append(thread)
    #     thread.start()
    
    # for t in threads:
    #     t.join()
    # print("Main thread finished!")
    
    #Daemon thread stops when the main thread stops
    
    #Threads with sync and locks-> When 2 threads try to access the same memory, hence we need to use locks
# counter=0
# counter_lock=Lock()
# def increment():
#     global counter
#     for _ in range(10000):
#         with counter_lock:
#             counter += 1

# if __name__=='__main__':
    #At module level (top of the file, inside if __name__ == '__main__':), you're already in the global scope.
    #global counter
    # if you define your main as def main(): and give global counter then t wouldn't show error
    
    
    
    # threads=[]
    # for i in range(3):
    #     thread=Thread(target=increment)
    #     threads.append(thread)
    #     thread.start()
    # for t in threads:
    #     t.join()
    # print("Counter value: ",counter)     
    


import concurrent.futures
import time

def task(n):
    print(f"Task {n} is starting")
    time.sleep(n)
    print(f"Task {n} is complete")
    return n*n

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        res=executor.map(task,range(1,6))
    
    print("Results: ",list(res))
    print("Main thread is finished")
    

if __name__=='__main__':
    main()
    