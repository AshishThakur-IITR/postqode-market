import sys
import os
import shutil
from sqlalchemy import text

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.agent_adapter import AgentAdapter
from app.models.agent_deployment import AgentDeployment
from app.models.license import License
# We are NOT deleting Users or Organizations to preserve accounts

def clean_db():
    db = SessionLocal()
    try:
        print("Cleaning database tables (keeping Users)...")
        # Order matters for foreign keys
        
        # 1. Delete deployments (relies on Agent and License)
        db.query(AgentDeployment).delete()
        print("- Deleted AgentDeployments")

        # 2. Delete licenses (relies on Agent and User)
        db.query(License).delete()
        print("- Deleted Licenses")
        
        # 3. Delete adapters (relies on Agent)
        db.query(AgentAdapter).delete()
        print("- Deleted AgentAdapters")
        
        # 4. Delete agent versions (relies on Agent)
        db.query(AgentVersion).delete()
        print("- Deleted AgentVersions")
        
        # 5. Delete agents (relies on Publisher/User)
        db.query(Agent).delete()
        print("- Deleted Agents")
        
        db.commit()
        print("Database cleaned successfully.")
    except Exception as e:
        print(f"Error cleaning DB: {e}")
        db.rollback()
    finally:
        db.close()

def clean_storage():
    print("Cleaning storage directories...")
    storage_path = os.path.join(backend_dir, "storage")
    
    dirs_to_clean = ["packages", "docker_images", "docker_builds"]
    
    for d in dirs_to_clean:
        path = os.path.join(storage_path, d)
        if os.path.exists(path):
            # Remove all contents but keep the dir
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print(f"Failed to remove {item_path}: {e}")
            print(f"- Cleaned {path}")
        else:
            print(f"- Creating {path}")
            os.makedirs(path, exist_ok=True)

if __name__ == "__main__":
    print(f"Starting cleanup on {backend_dir}")
    clean_db()
    clean_storage()
