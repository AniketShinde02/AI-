import asyncio
from fastapi import HTTPException

# Global Semaphore to limit concurrent calls
call_semaphore = None

def get_semaphore():
    global call_semaphore
    from config import MAX_CONCURRENT_CALLS
    if call_semaphore is None:
        call_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)
    return call_semaphore

async def acquire_call_slot():
    sem = get_semaphore()
    if sem.locked():
        raise HTTPException(status_code=429, detail="Voice worker overloaded. Try again later.")
    await sem.acquire()
    return True

def release_call_slot():
    sem = get_semaphore()
    sem.release()
