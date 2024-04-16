# Cache-modeling

## Introduction

The modeled cache is used only for working with data (not commands).

Addition, variable initialization, loop iteration, and function exit take 1 cycle. Multiplication takes 5 cycles.
Accessing memory in the form of pc[x] is counted as one command.

Arrays are stored sequentially in memory, the first one starting at address 0x40000.

All local variables are stored in processor registers.
Default initialization (RESET) – all cache lines are in the invalid state.


## "Processor-cache-memory" system

Variables, parameters, constants:

- MEM_SIZE – memory size (in bytes)

- CACHE_SIZE – cache size, excluding service information (in bytes)


- CACHE_LINE_SIZE – cache line size (in bytes)


- CACHE_LINE_COUNT – number of cache lines


- CACHE_WAY – associativity


- CACHE_SETS_COUNT – number of cache line blocks


- ADDR_LEN – address length (in bits)


- CACHE_TAG_LEN – address tag length (in bits)


- CACHE_IDX_LEN – cache line block index length (in bits)


- CACHE_OFFSET_LEN – offset length within a cache line (in bits)


### Cache line structure

| flags  | tag | data |
| ------------- | ------------- | ------------- |
| (as required)  | CACHE_TAG_LEN | CACHE_LINE_SIZE  |

Interpretation of the address by the cache (leftmost bits to rightmost bits):

| tag  | idx | offset |
| ------------- | ------------- | ------------- |
| CACHE_TAG_LEN  | CACHE_IDX_LEN | CACHE_OFFSET_LEN  |

### Bus sizes

| Bus  | Designation | Size |
| ------------- | ------------- | ------------- |
| A1, A2  | ADDR1_BUS_LEN, ADDR2_BUS_LEN | 16, 16 bits  |
| D1, D2  | DATA1_BUS_LEN, DATA2_BUS_LEN | 16 bits  |
| C1, C2  | CTR1_BUS_LEN, CTR2_BUS_LEN | 3, 2 bits  |

## Time

Response time – the number of cycles from the first command cycle to the first response cycle.
For the modeled system:
- 6 cycles – time for cache hit response to start responding.


- 4 cycles – time for cache miss response to send a request to memory.


- 100 cycles – time for memory to start responding.
Data transmission time on buses for the modeled system:


- Address is transmitted in 1 cycle on buses A1 and A2.


- Data of 16 bits is transmitted every cycle on buses D1 and D2.


- Command is transmitted in 1 cycle on buses C1 and C2.