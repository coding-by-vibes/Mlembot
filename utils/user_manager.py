import json
import logging
from pathlib import Path
from typing import Dict, Any

class UserManager:
    def __init__(self, settings_dir: str):
        self.logger = logging.getLogger(__name__)
        self.settings_dir = Path(settings_dir)
        self.users_dir = self.settings_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.user_settings: Dict[str, Dict[str, Any]] = {}
        self._load_all_users()

    def _user_file(self, user_id: str) -> Path:
        return self.users_dir / f"{user_id}.json"

    def _load_all_users(self):
        for user_file in self.users_dir.glob("*.json"):
            try:
                user_id = user_file.stem
                with open(user_file, "r", encoding="utf-8") as f:
                    self.user_settings[user_id] = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load user {user_file.name}: {e}")

    def load_user_data(self, user_id: str) -> Dict[str, Any]:
        if user_id in self.user_settings:
            return self.user_settings[user_id]

        file_path = self._user_file(user_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_settings[user_id] = data
                    return data
            except Exception as e:
                self.logger.error(f"Error reading user data for {user_id}: {e}")

        return self._create_default_user(user_id)

    def _create_default_user(self, user_id: str) -> Dict[str, Any]:
        data = {
            "joined": str(Path().stat().st_ctime),
            "preferences": {},
        }
        self.save_user_data(user_id, data)
        return data

    def save_user_data(self, user_id: str, data: Dict[str, Any]):
        try:
            with open(self._user_file(user_id), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.user_settings[user_id] = data
        except Exception as e:
            self.logger.error(f"Error saving user data for {user_id}: {e}")
