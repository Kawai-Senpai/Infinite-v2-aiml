from database.mongo import client as mongo_client
from bson import ObjectId

def get_memory(agent_id: str, user_id: str) -> list:
    db = mongo_client.ai.memory
    memory_doc = db.find_one({"agent_id": ObjectId(agent_id), "user_id": str(user_id)})
    if not memory_doc:
        return []
    return memory_doc.get("items", [])

def update_memory(agent_id: str, user_id: str, max_size: int, new_items: list):
    """Append the new items to memory and ensure it doesn't exceed max_size."""
    db = mongo_client.ai.memory
    memory_doc = db.find_one({"agent_id": ObjectId(agent_id), "user_id": str(user_id)})
    if not memory_doc:
        memory_doc = {
            "agent_id": ObjectId(agent_id),
            "user_id": str(user_id),
            "items": []
        }

    memory = memory_doc["items"]
    memory.extend(new_items)
    if len(memory) > max_size:
        memory = memory[-max_size:]

    db.update_one(
        {"agent_id": ObjectId(agent_id), "user_id": str(user_id)},
        {"$set": {"items": memory}}, 
        upsert=True
    )
