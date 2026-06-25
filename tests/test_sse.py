import asyncio

import pytest

from backend.db.sse_manager import SSEConnectionManager


async def test_broadcast_reaches_subscriber():
    manager = SSEConnectionManager()
    queue = await manager.subscribe("*")
    await manager.broadcast("my-flag", '{"key":"my-flag"}')
    msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert msg == '{"key":"my-flag"}'


async def test_unsubscribe_stops_messages():
    manager = SSEConnectionManager()
    queue = await manager.subscribe("*")
    await manager.unsubscribe("*", queue)
    await manager.broadcast("my-flag", "hello")
    assert queue.empty()


async def test_full_queue_does_not_block_broadcast():
    manager = SSEConnectionManager()
    queue = await manager.subscribe("*")
    for _ in range(101):  # maxsize is 100
        await manager.broadcast("flag", "data")
    # Should not raise or block


async def test_broadcast_reaches_flag_specific_subscriber():
    manager = SSEConnectionManager()
    queue = await manager.subscribe("my-flag")
    await manager.broadcast("my-flag", '{"key":"my-flag"}')
    msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert msg == '{"key":"my-flag"}'


async def test_broadcast_does_not_reach_other_flag_subscriber():
    manager = SSEConnectionManager()
    queue = await manager.subscribe("other-flag")
    await manager.broadcast("my-flag", "hello")
    assert queue.empty()


async def test_multiple_subscribers_all_receive():
    manager = SSEConnectionManager()
    q1 = await manager.subscribe("*")
    q2 = await manager.subscribe("*")
    await manager.broadcast("my-flag", "payload")
    msg1 = await asyncio.wait_for(q1.get(), timeout=1.0)
    msg2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert msg1 == "payload"
    assert msg2 == "payload"


async def test_global_and_specific_both_receive():
    """A broadcast to 'my-flag' should reach both '*' and 'my-flag' subscribers."""
    manager = SSEConnectionManager()
    q_global = await manager.subscribe("*")
    q_specific = await manager.subscribe("my-flag")
    await manager.broadcast("my-flag", "payload")
    msg_global = await asyncio.wait_for(q_global.get(), timeout=1.0)
    msg_specific = await asyncio.wait_for(q_specific.get(), timeout=1.0)
    assert msg_global == "payload"
    assert msg_specific == "payload"
