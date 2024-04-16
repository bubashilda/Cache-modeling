import math
from abc import ABC, abstractmethod

ADDR_LEN = 20
CACHE_LINE_SIZE = 128
CACHE_WAY = 4
CACHE_TAG_LEN = 9
CACHE_OFFSET_LEN = int(math.log2(CACHE_LINE_SIZE))  # 7
CACHE_IDX_LEN = ADDR_LEN - CACHE_TAG_LEN - CACHE_OFFSET_LEN  # 4
CACHE_SETS_COUNT = 2 ** CACHE_IDX_LEN  # 16
CACHE_LINE_COUNT = CACHE_SETS_COUNT * CACHE_WAY  # 64

DATA1_BUS_LEN = DATA2_BUS_LEN = 16
ADDR1_BUS_LEN = ADDR2_BUS_LEN = 20  # address transfers within 1 tact
CTR1_BUS_LEN = int(math.log2(8))
CTR2_BUS_LEN = int(math.log2(4))


CACHE_SIZE = CACHE_LINE_COUNT * CACHE_LINE_SIZE  # 8192
MEM_SIZE = 2 ** ADDR_LEN  # 1048576

M = 64
N = 60
K = 32

a = 0x40000              # M x K
a_int_byte_size = 1
b = a + M * K * 1        # K x N
b_int_byte_size = 2
c = b + K * N * 2        # M x N
c_int_byte_size = 4

'''
Without cache-miss:
read = 1 (query + address) + 6 (cache ping) + 
       math.ceil(byte_count * 8 / DATA1_BUS_LEN) (receive data from cache) + 1 (response)

write = 1 (query + address) + max(6 (cache ping), math.ceil(byte_count * 8 / DATA1_BUS_LEN) (data transfer)) 
        + 1 (response)

With cache-miss:
throw_dirty_line = 1 (query + address) + max(100 (mem ping), 
                   math.ceil(CACHE_LINE_SIZE * 8 / DATA2_BUS_LEN) (data transfer)) + 1 (response)

read = 1 (query + address) + 4 (cache ping) + ?throw_dirty_line? + 1 (query_mem) + 100 (mem ping) +
       math.ceil(CACHE_LINE_SIZE * 8 / DATA2_BUS_LEN) (data transfer) + 1 (response_mem) + 
       math.ceil(byte_count * 8 / DATA1_BUS_LEN) + 1 (response)

write = 1 (query + address) + max(math.ceil(byte_count * 8 / DATA1_BUS_LEN), 4 (cache ping) + 
        ?throw_dirty_line? + 1 (response))
'''


class Handler:

    address_mask = 2 ** ADDR_LEN - 1
    mask_tag = address_mask & ~(2 ** (CACHE_OFFSET_LEN + CACHE_IDX_LEN) - 1)
    mask_idx = address_mask & ~(2 ** CACHE_OFFSET_LEN - 1) & ~mask_tag
    mask_offset = address_mask & ~mask_idx & ~mask_tag

    @staticmethod
    def get_tag(address):
        return (address & Handler.mask_tag) >> (CACHE_OFFSET_LEN + CACHE_IDX_LEN)

    @staticmethod
    def get_ind(address):
        return (address & Handler.mask_idx) >> CACHE_OFFSET_LEN

    @staticmethod
    def get_offset(address):
        return address & Handler.mask_offset


class CacheLine:

    def __init__(self):
        self.flags = {
            'V': 0,
            'D': 0,
            'PLRU': 0,
            'LRU': CACHE_WAY - 1
        }
        self.tag = 0x0


class Set:

    def __init__(self):
        self.lines = [CacheLine() for i in range(CACHE_WAY)]


class Cache(ABC):

    throw_dirty_line = 2 + max(100, math.ceil(CACHE_LINE_SIZE * 8 / DATA2_BUS_LEN))

    def __init__(self):
        self.sets = [Set() for i in range(CACHE_SETS_COUNT)]
        self.requestCount = 0
        self.hitCount = 0
        self.time = 0

    def get_hit_rate(self):
        return self.hitCount / self.requestCount

    def get_time(self):
        return self.time

    def update_time(self, time):
        self.time += time

    def update_counters(self, miss):
        self.requestCount += 1
        self.hitCount += 1 if not miss else 0

    def check_miss(self, address):
        ind = Handler.get_ind(address)
        tag = Handler.get_tag(address)
        for line in self.sets[ind].lines:
            if line.flags['V'] == 1 and line.tag == tag:
                return False
        return True

    def have_to_throw(self, address):
        flags = self.sets[Handler.get_ind(address)].lines[self.find_ind_of_line(address)].flags
        if flags['V'] == flags['D'] == 1:
            return True
        return False

    def find_ind_of_line(self, address):
        ind = Handler.get_ind(address)
        tag = Handler.get_tag(address)
        i = 0
        for line in self.sets[ind].lines:
            if line.flags['V'] == 1 and line.tag == tag:
                return i
            i += 1
        return -1

    def read_from_ram(self, address):
        ind_line = self.find_index_to_replace(address)
        ind_set = Handler.get_ind(address)
        tag = Handler.get_tag(address)
        self.sets[ind_set].lines[ind_line].flags['D'] = 0
        self.sets[ind_set].lines[ind_line].flags['V'] = 1
        self.sets[ind_set].lines[ind_line].tag = tag

    def write_back_absent(self, address):
        ind = Handler.get_ind(address)
        tag = Handler.get_tag(address)
        change = self.find_index_to_replace(address)
        self.sets[ind].lines[change].flags['D'] = 1
        self.sets[ind].lines[change].flags['V'] = 1
        self.sets[ind].lines[change].tag = tag

    def write_back_consists(self, address):
        ind_line = self.find_ind_of_line(address)
        ind_set = Handler.get_ind(address)
        tag = Handler.get_tag(address)
        self.sets[ind_set].lines[ind_line].flags['D'] = 1
        self.sets[ind_set].lines[ind_line].flags['V'] = 1
        self.sets[ind_set].lines[ind_line].tag = tag

    def make_request_to_read(self, address, byte_count):
        miss = self.check_miss(address)
        if miss:
            self.update_time(108 + self.have_to_throw(address) * self.throw_dirty_line
                             + math.ceil(CACHE_LINE_SIZE * 8 / DATA2_BUS_LEN)
                             + math.ceil(byte_count * 8 / DATA1_BUS_LEN))
            self.read_from_ram(address)
        else:
            self.update_time(8 + math.ceil(byte_count * 8 / DATA1_BUS_LEN))
            pass
        self.change_lru_indicator(address)
        self.update_counters(miss)

    def make_request_to_write(self, address, byte_count):
        miss = self.check_miss(address)
        if miss:
            self.write_back_absent(address)
            self.update_time(1 + max(self.have_to_throw(address) * self.throw_dirty_line + 5,
                                     + math.ceil(byte_count * 8 / DATA1_BUS_LEN)))
        else:
            self.update_time(2 + max(6, math.ceil(byte_count * 8 / DATA1_BUS_LEN)))
            self.write_back_consists(address)
        self.change_lru_indicator(address)
        self.update_counters(miss)

    @abstractmethod
    def change_lru_indicator(self, address):
        pass

    @abstractmethod
    def find_index_to_replace(self, address):
        pass


class LRUCache(Cache):

    def change_lru_indicator(self, address):
        ind = Handler.get_ind(address)
        ind_line = self.find_ind_of_line(address)
        current_usage = self.sets[ind].lines[ind_line].flags['LRU']
        for line in self.sets[ind].lines:
            if line.flags['LRU'] < current_usage:
                line.flags['LRU'] += 1
        self.sets[ind].lines[ind_line].flags['LRU'] = 0

    def find_index_to_replace(self, address):
        ind = Handler.get_ind(address)
        change = -1
        i = 0
        for line in self.sets[ind].lines:
            if line.flags['LRU'] == CACHE_WAY - 1:
                change = i
            i += 1
        return change


class PLRUCache(Cache):

    def change_lru_indicator(self, address):
        ind = Handler.get_ind(address)
        ind_line = self.find_ind_of_line(address)
        count_zeros = 0
        self.sets[ind].lines[ind_line].flags['PLRU'] = 1
        for line in self.sets[ind].lines:
            if line.flags['PLRU'] == 0:
                count_zeros += 1
        if count_zeros == 0:
            for line in self.sets[ind].lines:
                line.flags['PLRU'] = 0
            self.sets[ind].lines[ind_line].flags['PLRU'] = 1

    def find_index_to_replace(self, address):
        ind = Handler.get_ind(address)
        change = -1
        i = 0
        for line in self.sets[ind].lines:
            if line.flags['PLRU'] == 0:
                change = i
            i += 1
        return change


def task(cache: Cache):
    pa = a
    pc = c
    cache.update_time(2)  # pointers initialization

    cache.update_time(1)  # m initialization
    for y in range(M):

        cache.update_time(1)  # n initialization
        for x in range(N):
            pb = b
            # s = 0
            cache.update_time(2)  # variable initialization

            cache.update_time(1)  # k initialization
            for k in range(K):
                # s += cache.request(pa + k * a_int_byte_size) * cache.request(pb + x * b_int_byte_size)
                cache.update_time(1 + 5)  # write to reg s: addition + multiplication
                cache.make_request_to_read(pa + k * a_int_byte_size, a_int_byte_size)
                cache.make_request_to_read(pb + x * b_int_byte_size, b_int_byte_size)
                pb += N * b_int_byte_size
                cache.update_time(1)  # write to reg pb: addition + addition

                cache.update_time(1 + 1)  # increment counter + new iteration

            cache.make_request_to_write(pc + x * c_int_byte_size, c_int_byte_size)
            cache.update_time(1 + 1)  # increment counter + new iteration

        pa += K * a_int_byte_size
        cache.update_time(1)  # write to reg pa: addition
        pc += N * c_int_byte_size
        cache.update_time(1)  # write to reg pc: addition
        cache.update_time(1 + 1)  # increment counter + new iteration

    cache.update_time(1)  # exit function


if __name__ == '__main__':
    lrucache = LRUCache()
    task(lrucache)
    plrucache = PLRUCache()
    task(plrucache)
    print(f'LRU:\thit perc. {round(lrucache.get_hit_rate() * 100, 4)}%\ttime: {lrucache.get_time()}')
    print(f'pLRU:\thit perc. {round(plrucache.get_hit_rate() * 100, 4)}%\ttime: {plrucache.get_time()}')

