import os
import sys
import shutil
from dotenv import load_dotenv
from qdrant_client import models

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import red_pill.config as cfg
from red_pill.memory import MemoryManager

def verify():
    print("🔴 Verifying Local Qdrant (Embedded Mode)")
    
    # Force set QDRANT_PATH for this test if not set, or use what's in env
    db_path = os.getenv("QDRANT_PATH", "test_local_qdrant_db")
    
    # Clean up previous test if exists
    if os.path.exists(db_path):
        print(f"🧹 Cleaning up previous test database at: {db_path}")
        try:
            shutil.rmtree(db_path)
        except Exception as e:
            print(f"⚠️ Could not remove directory {db_path}: {e}")
            # Try to proceed anyway, or abort? 
            # If Qdrant holds a lock file, this might fail.
    
    print(f"📂 Database Path: {db_path}")
    
    # Temporarily override config
    cfg.QDRANT_PATH = db_path
    
    try:
        print("🔌 Initializing MemoryManager (should create local DB)...")
        memory = MemoryManager(path=db_path)
        
        # Ensure collection exists
        if not memory.client.collection_exists("test_collection"):
             print("🆕 Creating collection 'test_collection'...")
             memory.client.create_collection(
                 collection_name="test_collection",
                 vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
             )
        
        # Add a test memory
        print("🧠 Adding a test memory...")
        memory.add_memory("test_collection", "This is a test memory regarding local storage.")
        
        # Verify collection exists and has points
        print("🔍 Verifying collection stats...")
        stats = memory.get_stats("test_collection")
        print(f"   Stats: {stats}")
        
        if stats['points_count'] > 0:
            print("✅ Success! Memory stored locally.")
        else:
            print("❌ Error: Memory count is 0.")

    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    verify()
