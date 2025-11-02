#include<iostream>
#include<mutex>
using namespace std;

class Singleton{
    // public:
    //     Singleton(){
    //         cout<<"Singleton constructor called"<<endl;
    //     }
    private:
        static Singleton* instance;
        //Declaring above vairbale for pointer of object creation
        //Intialy it is null. Every time user tries to create the object
        //We would return instance variable
        //We need to intialize above variable outside

        static mutex mtx; //Helps lock and unlock critical section of the code
        //so that multiple threads can't access it simultaneously

        Singleton(){
            cout<<"Singleton constructor called"<<endl;
        }
    public:
        static Singleton* getInstance(){
            // lock_guard<mutex> lock(mtx); //Lock for thread safety
            // if(instance==nullptr){
            //     instance=new Singleton();
            // }
            // return instance;  
            
            //Above code is expensive since we are not checking if instance is nullptr
            //Suppose thread enters this method and object is not created so there is
            // no need to apply lock

            // if(instance==nullptr){
            //     lock_guard<mutex> lock(mtx);
            //     instance=new Singleton();
            // }
            // return instance;

            //But above code would still create 2 objects
            //Suppose we have 2 threads t1 and t2 both checks instace==null
            //t1 will lock and then create instance object exit the block and unlock it
            //But t2 would have entered inside the if method and siting on the line where
            //the lock is present and as soon as t1 unlocks it t2 would create another
            //instance object

            if(instance==nullptr){
                lock_guard<mutex> lock(mtx);
                if(instance==nullptr){
                    instance=new Singleton();
                }
                
            }
            return instance;

            //Above is similar to thread safe 
        }
};
Singleton *Singleton::instance=nullptr;
//Classname objectname method value 
int main(){
    //Our goal is to restric user from creating multiple object
    //Singleton class can have only one object created
    // Singleton* s1=new Singleton();
    // Singleton* s2=new Singleton();

    // cout<<(s1==s2)<<endl; 
    //Above output is 0
    //s1 and s2 are pointer which are pointing to object in the heap memory
    //Object is only created since contructor is public

    Singleton* s1=Singleton::getInstance();
    Singleton* s2=Singleton::getInstance();

    cout<<(s1==s2)<<endl;
    return 0;

}

//Above Singleton class is not thread safe
//getInstance method would be executed by multiple threads
//Hence those threads can enter the getInstance method and create the object simultaneoulsy
//We would introduce locking
//But locking and unlocking are expensive operations


//Eager instialization

// static Singleton* getInstance(){
//     return instance;

// }
// Singleton *Singleton::instance=new Singleton();

//While declaring instance pointer we can create the object of the class using new keyword
//But this operation might be memory expensive 
//Suppose we dont call the object or never use the method of the class
//Only use it when object is lightweight

//Real world usage
//Logging system,Database connection, Confguration manager
