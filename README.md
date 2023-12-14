# DNS-Resolver Implementation
Install requirements with ```pip install requirements.txt```.

Run the program with ```python resolver.py```.


There are some command-line flags:
| Option | Description |
| :--------: | :----------:|
| ```--method TYPE``` | Options are ```recursive ``` or ```iterative``` to choose which search method to use. Default is ```recursive```.|
| ```--verbose```| Provides more detailed information, including how long queries take and if a value is in the cache.|

Queries to the resolver are of the form ```<domain name> [record type]``` (or ```q``` to quit). Supported record types are ```A, AAAA, TXT```, with the option of using a record type ```ANY``` to query all three at once.