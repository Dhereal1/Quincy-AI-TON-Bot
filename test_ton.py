import asyncio
import requests
from pytonlib import TonlibClient

async def test_connection():
    # 1. Download the latest Mainnet config
    config_url = 'https://ton.org/global.config.json'
    config = requests.get(config_url).json()
    
    # 2. Setup the client
    # 'keystore' is where the library saves security keys
    client = TonlibClient(ls_index=0, config=config, keystore='/tmp/ton_keystore')
    
    try:
        print("⏳ Initializing TON client (this can take a few seconds)...")
        await client.init()
        print("✅ Success! Quincy is connected to the TON Blockchain.")
        
        # Test: Get the masterchain information
        masterchain_info = await client.get_masterchain_info()
        print(f"🔗 Current Block: {masterchain_info['last']['seqno']}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
