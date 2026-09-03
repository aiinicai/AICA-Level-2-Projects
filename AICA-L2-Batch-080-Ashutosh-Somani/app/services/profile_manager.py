import os
import json
import uuid
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from app.models.profile import BankProfile
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, config):
        self.config = config
        
        if hasattr(config, 'get') and hasattr(config, 'read'): # ConfigParser
            prof_dir_str = config.get('paths', 'profiles', fallback='profiles')
            backup_dir_str = config.get('paths', 'backups', fallback=os.path.join(prof_dir_str, 'backups'))
        elif hasattr(config, 'get') and 'APP_CONFIG' in config: # Flask Config
            real_config = config['APP_CONFIG']
            prof_dir_str = real_config.get('paths', 'profiles', fallback='profiles')
            backup_dir_str = real_config.get('paths', 'backups', fallback=os.path.join(prof_dir_str, 'backups'))
        else:
            prof_dir_str = 'profiles'
            backup_dir_str = os.path.join(prof_dir_str, 'backups')
        
        # Absolute project root resolution
        project_root = Path(__file__).resolve().parent.parent.parent
        
        # Ensure paths are absolute by resolving against project_root if not already absolute
        p_dir = Path(prof_dir_str)
        self.profiles_dir = p_dir if p_dir.is_absolute() else project_root / p_dir
        
        b_dir = Path(backup_dir_str)
        self.backups_dir = b_dir if b_dir.is_absolute() else project_root / b_dir
        
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_path(self, profile_id: str) -> Path:
        # Prevent path traversal
        clean_id = os.path.basename(profile_id)
        return self.profiles_dir / f"{clean_id}.json"

    def list_profiles(self) -> List[BankProfile]:
        """Loads all valid profiles from the profiles directory."""
        profiles = []
        for file_path in self.profiles_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    prof = BankProfile.from_dict(data)
                    profiles.append(prof)
            except Exception as e:
                logger.error(f"Failed to load profile {file_path}: {e}")
        return profiles
        
    def get_profile(self, profile_id: str) -> Optional[BankProfile]:
        path = self._get_path(profile_id)
        if not path.exists():
            return None
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BankProfile.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load profile {profile_id}: {e}")
            return None

    def save_profile(self, profile: BankProfile, create_backup: bool = True) -> bool:
        """Atomic write with revision increment and backup."""
        path = self._get_path(profile.profile_id)
        
        # Backup existing
        if path.exists() and create_backup:
            try:
                existing = self.get_profile(profile.profile_id)
                if existing:
                    profile.revision_number = existing.revision_number + 1
                    
                timestamp = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S")
                backup_path = self.backups_dir / f"{profile.profile_id}_{timestamp}_rev{existing.revision_number if existing else 0}.json"
                shutil.copy2(path, backup_path)
            except Exception as e:
                logger.error(f"Failed to backup profile {profile.profile_id}: {e}")
                return False
                
        profile.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        
        # Atomic Write
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
                
            os.replace(temp_path, path)
            
            # Sync to DB Index
            self._sync_index(profile)
            return True
        except Exception as e:
            logger.error(f"Failed to save profile {profile.profile_id}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False
            
    def _sync_index(self, profile: BankProfile):
        try:
            with get_db_connection(self.config) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bank_profiles (profile_id, profile_name, bank_name, profile_revision, active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(profile_id) DO UPDATE SET
                        profile_name=excluded.profile_name,
                        bank_name=excluded.bank_name,
                        profile_revision=excluded.profile_revision,
                        active=excluded.active,
                        updated_at=excluded.updated_at
                ''', (
                    profile.profile_id,
                    profile.profile_name,
                    profile.bank_name,
                    profile.revision_number,
                    profile.active,
                    profile.updated_at
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to sync profile {profile.profile_id} to SQLite: {e}")

    def create_profile(self, name: str, bank: str) -> BankProfile:
        prof = BankProfile(
            profile_id=str(uuid.uuid4()),
            profile_name=name,
            bank_name=bank
        )
        self.save_profile(prof, create_backup=False)
        return prof

    def deactivate_profile(self, profile_id: str) -> bool:
        prof = self.get_profile(profile_id)
        if prof:
            prof.active = False
            return self.save_profile(prof)
        return False
        
    def clone_profile(self, profile_id: str, new_name: str) -> Optional[BankProfile]:
        prof = self.get_profile(profile_id)
        if not prof:
            return None
            
        prof.profile_id = str(uuid.uuid4())
        prof.profile_name = new_name
        prof.revision_number = 1
        prof.created_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        prof.updated_at = prof.created_at
        
        if self.save_profile(prof, create_backup=False):
            return prof
        return None

    def import_profile(self, data: dict, handle_duplicate="clone") -> Tuple[bool, str]:
        """Imports a JSON profile safely."""
        try:
            # Basic schema val
            if "profile_name" not in data or "bank_name" not in data:
                return False, "Missing required fields"
                
            prof = BankProfile.from_dict(data)
            
            existing = self.get_profile(prof.profile_id)
            if existing:
                if handle_duplicate == "clone":
                    prof.profile_id = str(uuid.uuid4())
                    prof.profile_name = f"{prof.profile_name} (Imported Clone)"
                    prof.revision_number = 1
                elif handle_duplicate == "reject":
                    return False, "Profile ID already exists"
                else: # overwrite
                    prof.revision_number = existing.revision_number + 1
                    
            self.save_profile(prof)
            return True, prof.profile_id
            
        except Exception as e:
            return False, f"Import failed: {str(e)}"
