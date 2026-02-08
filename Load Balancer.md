Load Balancer->We have our application and we want to distribute the load among copies of our application

 

API Gateway->Central point from which you are distributing the request to different micoroservices

 	     Performes authorization

 

Reverse Proxy->Hiding the identity of backend system

 	       Caching static content







Db strategies



&nbsp;	Vertical Scaling->Increase CPU power

&nbsp;			  Adding more RAM

&nbsp;			  Adding more disk

&nbsp;			  Upgrading network



&nbsp;	Horizontal Scaling->DB sharding->Distributing various parts of the db across various servers

&nbsp;						Range based

&nbsp;						Directory based sharding

&nbsp;						Geographical based sharding	  

&nbsp;		            Replication->Keeping copies of db on multiple servers

&nbsp;						Master db for read/write and other slaves for read only

&nbsp;						Both master and slave for read/write

&nbsp;	

&nbsp;	DB caching->Cache frequent queries to boost performance

&nbsp;	

&nbsp;	Index->Index frequently accessed columns

&nbsp;	

&nbsp;	Query optimization-> minimizing joins



&nbsp;	CAP->Consistency Availability and Partition. You can only optimize 2/3





DB indexing

&nbsp;	Index is a separate data structure that maintains sorted searchable copy of certain column

&nbsp;	along with pointers to the actual rows

&nbsp;	

&nbsp;	We use B trees



&nbsp;		Primary index-> Data is physically organized by this index.



&nbsp;		create table users(

&nbsp;			...

&nbsp;			...

&nbsp;		);



&nbsp;		

&nbsp;		Secondary index->Separate structure that point back to the primary key.

&nbsp;				create index index\_name on table\_name(col\_name);

&nbsp;		

More indexes can make operation slow in case of write and update operations as you need to modify indexes as well

Check for col where you do constant lookups. Use those cols to create index.

If we use foreign key col index it



When not to index?

&nbsp;	Small table

&nbsp;	Rarely queries

&nbsp;	Low selectivity

&nbsp;	Heavily write/updated





Sharding

&nbsp;	Router and config server

&nbsp;	Router->read/write and decides which server to send data

&nbsp;	Config ->stores sharding algorithm and knows how data is split



&nbsp;	So router checks the config server to check where to send the data



&nbsp;	We need to keep in mind the following

&nbsp;		Even distribution

&nbsp;		Add Shards

&nbsp;		Delete/Failed shards

&nbsp;	



&nbsp;	Sharding types

&nbsp;		Simple hashing-> S\[i]=row\_id%n

&nbsp;			Works find until we need to add new row or a shard goes

&nbsp;		

&nbsp;		Consistent hashing->

&nbsp;			Shards are distributed in circle and

&nbsp;			

&nbsp;			User\_id%number\_shards=X\[i]



&nbsp;		s1	s2	s3		sn

&nbsp;	-----------------------------------------

&nbsp;       0	x0	x1	x2	x3	P





&nbsp;			We also replicate the data in case a shard goes down

&nbsp;			Hence request coming to failed shard would go to new shard

&nbsp;		

&nbsp;			



&nbsp;		

&nbsp;			

&nbsp;	

























&nbsp;

