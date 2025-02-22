from database.mongo import client as mongo_client
from bson import ObjectId

def get_memory(agent_id: str, user_id: str) -> list:
    """
    Retrieve the memory items for a given agent and user.

    Args:
        agent_id (str): The ID of the agent.
        user_id (str): The ID of the user.

    Returns:
        list: A list of memory items.
    """
    db = mongo_client.ai.memory
    memory_doc = db.find_one({"agent_id": ObjectId(agent_id), "user_id": str(user_id)})
    if not memory_doc:
        return []
    return memory_doc.get("items", [])

def update_memory(agent_id: str, user_id: str, max_size: int, new_items: list):
    """
    Update the memory for a given agent and user.

    This function appends new items to the memory and ensures it doesn't exceed the maximum size.

    Args:
        agent_id (str): The ID of the agent.
        user_id (str): The ID of the user.
        max_size (int): The maximum size of the memory.
        new_items (list): A list of new memory items to add.
    """
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
