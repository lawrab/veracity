#!/usr/bin/env python3
"""Test WebSocket functionality."""

import asyncio
import json
import websockets
import time


async def test_websocket_connection():
    """Test basic WebSocket connection and messaging."""
    uri = "ws://localhost:8000/api/v1/ws/v2/connect?channel=test"
    
    print("1. Testing basic connection...")
    async with websockets.connect(uri) as websocket:
        # Wait for connection message
        message = await websocket.recv()
        data = json.loads(message)
        print(f"   ✓ Connected: {data['type']} on channel {data.get('channel')}")
        
        # Test ping-pong
        print("\n2. Testing heartbeat (ping-pong)...")
        ping_msg = await websocket.recv()
        ping_data = json.loads(ping_msg)
        if ping_data['type'] == 'ping':
            await websocket.send(json.dumps({'type': 'pong'}))
            print("   ✓ Received ping, sent pong")
        
        # Test subscription
        print("\n3. Testing channel subscription...")
        await websocket.send(json.dumps({
            'type': 'subscribe',
            'channel': 'stories'
        }))
        sub_response = await websocket.recv()
        sub_data = json.loads(sub_response)
        print(f"   ✓ Subscribed to channel: {sub_data}")
        
        # Test echo
        print("\n4. Testing message echo...")
        test_msg = {'type': 'test', 'data': 'Hello WebSocket!'}
        await websocket.send(json.dumps(test_msg))
        echo_response = await websocket.recv()
        echo_data = json.loads(echo_response)
        print(f"   ✓ Echo received: {echo_data}")
        
        print("\n✅ Basic WebSocket tests passed!")


async def test_rate_limiting():
    """Test rate limiting functionality."""
    uri = "ws://localhost:8000/api/v1/ws/v2/connect?channel=rate_test"
    
    print("\n5. Testing rate limiting (sending 105 messages)...")
    async with websockets.connect(uri) as websocket:
        # Skip initial connection message
        await websocket.recv()
        
        messages_sent = 0
        rate_limited = False
        
        for i in range(105):
            await websocket.send(json.dumps({
                'type': 'test',
                'data': f'Message {i}'
            }))
            messages_sent += 1
            
            # Check for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                data = json.loads(response)
                if data.get('type') == 'error' and 'Rate limit' in data.get('message', ''):
                    rate_limited = True
                    print(f"   ✓ Rate limited after {messages_sent} messages")
                    break
            except asyncio.TimeoutError:
                continue
        
        if rate_limited:
            print("   ✅ Rate limiting works!")
        else:
            print("   ⚠️  Rate limiting may not be triggered (check configuration)")


async def test_multiple_connections():
    """Test multiple concurrent connections."""
    print("\n6. Testing multiple concurrent connections...")
    
    connections = []
    for i in range(5):
        uri = f"ws://localhost:8000/api/v1/ws/v2/connect?channel=conn_test_{i}"
        ws = await websockets.connect(uri)
        connections.append(ws)
        # Read connection message
        await ws.recv()
    
    print(f"   ✓ Established {len(connections)} concurrent connections")
    
    # Check stats
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/v1/ws/v2/stats') as resp:
            stats = await resp.json()
            print(f"   ✓ Stats: {stats}")
    
    # Close all connections
    for ws in connections:
        await ws.close()
    
    print("   ✅ Multiple connections test passed!")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("WebSocket Testing Suite")
    print("=" * 50)
    
    try:
        await test_websocket_connection()
        await test_rate_limiting()
        await test_multiple_connections()
        
        print("\n" + "=" * 50)
        print("🎉 All WebSocket tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())