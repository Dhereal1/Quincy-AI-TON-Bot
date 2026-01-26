import os
from tonsdk.utils import Address
from dotenv import load_dotenv

load_dotenv()

# Let's try to format a raw address
test_address = "EQCD39VS5jcptHL8vMjEXnuab-v9YlrS-66sgfZEircSgYp7"
try:
    addr = Address(test_address)
    print(f"✅ Library working! Address is valid.")
    print(f"Human-readable: {addr.to_string(True, True, True)}")
except Exception as e:
    print(f"❌ Something is wrong: {e}")
