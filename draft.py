# draft.py — temporary storage for transaction drafts

user_drafts = {}  # user_id → draft_data

def save_draft(user_id: int, data: dict):
    user_drafts[user_id] = data

def get_draft(user_id: int):
    return user_drafts.get(user_id)

def clear_draft(user_id: int):
    if user_id in user_drafts:
        del user_drafts[user_id]
