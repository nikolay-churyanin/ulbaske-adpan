import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_admin_ids(raw):
    ids = set()
    for part in str(raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            logger.warning("Пропущен нечисловой ADMIN_IDS: %s", part)
    return ids


class AdminStore:
    def __init__(self, env_ids, file_path):
        self.env_ids = set(env_ids or set())
        self.file_path = Path(file_path)
        self.extra = []
        self._load()

    def _load(self):
        self.extra = []
        if not self.file_path.exists():
            return
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            for item in data.get("admins") or []:
                try:
                    admin_id = int(item.get("id"))
                except (TypeError, ValueError):
                    continue
                if admin_id in self.env_ids:
                    continue
                self.extra.append({
                    "id": admin_id,
                    "name": str(item.get("name") or admin_id),
                    "added_by": item.get("added_by"),
                })
        except Exception as error:
            logger.error("Не удалось прочитать %s: %s", self.file_path, error)

    def _save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "admins": [
                {
                    "id": item["id"],
                    "name": item.get("name") or str(item["id"]),
                    "added_by": item.get("added_by"),
                }
                for item in self.extra
            ]
        }
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def extra_ids(self):
        return {item["id"] for item in self.extra}

    def all_ids(self):
        return set(self.env_ids) | self.extra_ids()

    def is_admin(self, user_id):
        try:
            return int(user_id) in self.all_ids()
        except (TypeError, ValueError):
            return False

    def is_env_admin(self, user_id):
        try:
            return int(user_id) in self.env_ids
        except (TypeError, ValueError):
            return False

    def list_admins(self):
        listed = []
        for admin_id in sorted(self.env_ids):
            listed.append({"id": admin_id, "name": str(admin_id), "source": "env"})
        for item in sorted(self.extra, key=lambda row: row["id"]):
            listed.append({
                "id": item["id"],
                "name": item.get("name") or str(item["id"]),
                "source": "file",
            })
        return listed

    def add_admin(self, user_id, name=None, added_by=None):
        admin_id = int(user_id)
        if admin_id in self.all_ids():
            return False, "already"
        self.extra.append({
            "id": admin_id,
            "name": str(name or admin_id),
            "added_by": added_by,
        })
        self._save()
        return True, "added"

    def remove_admin(self, user_id):
        admin_id = int(user_id)
        if admin_id in self.env_ids:
            return False, "env"
        if admin_id not in self.extra_ids():
            return False, "missing"
        remaining = (self.all_ids() - {admin_id})
        if not remaining:
            return False, "last"
        self.extra = [item for item in self.extra if item["id"] != admin_id]
        self._save()
        return True, "removed"
