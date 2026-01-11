"""
Enhanced Rollback Manager for File Operations

This module provides a comprehensive rollback system with features:
- Multi-level version history
- Diff comparison between versions
- Snapshot management
- Batch rollback operations
- Version tagging
- Automatic cleanup of old backups
"""

import os
import json
import gzip
import base64
import shutil
import difflib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from colorama import Fore, Style


@dataclass
class FileVersion:
    """Represents a single version of a file"""
    version_id: str
    file_path: str
    timestamp: str
    content_b64: str  # gzip + base64 encoded content
    size_bytes: int
    operation: str  # edit, write, delete, etc.
    tags: List[str]
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FileVersion':
        """Create FileVersion from dictionary"""
        return FileVersion(**data)


@dataclass
class Snapshot:
    """Represents a snapshot of multiple files at a point in time"""
    snapshot_id: str
    timestamp: str
    description: str
    file_versions: Dict[str, str]  # {file_path: version_id}
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Snapshot':
        """Create Snapshot from dictionary"""
        return Snapshot(**data)


class RollbackManager:
    """
    Enhanced rollback manager with comprehensive version control features
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the rollback manager
        
        Args:
            storage_dir: Directory to store version history. If None, uses default location.
        """
        if storage_dir is None:
            from ..utils.logs import get_logs_root
            storage_dir = os.path.join(get_logs_root(), "rollback_storage")
        
        self.storage_dir = Path(storage_dir)
        self.versions_dir = self.storage_dir / "versions"
        self.snapshots_dir = self.storage_dir / "snapshots"
        self.index_file = self.storage_dir / "index.json"
        
        # Create directories
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory index
        self.file_versions: Dict[str, List[FileVersion]] = {}
        self.snapshots: Dict[str, Snapshot] = {}
        
        # Load existing index
        self._load_index()
    
    def _load_index(self) -> None:
        """Load the index from disk"""
        if not self.index_file.exists():
            return
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load file versions
            for file_path, versions_data in data.get('file_versions', {}).items():
                self.file_versions[file_path] = [
                    FileVersion.from_dict(v) for v in versions_data
                ]
            
            # Load snapshots
            for snapshot_id, snapshot_data in data.get('snapshots', {}).items():
                self.snapshots[snapshot_id] = Snapshot.from_dict(snapshot_data)
        
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Failed to load rollback index: {e}{Style.RESET_ALL}")
    
    def _save_index(self) -> None:
        """Save the index to disk"""
        try:
            data = {
                'file_versions': {
                    file_path: [v.to_dict() for v in versions]
                    for file_path, versions in self.file_versions.items()
                },
                'snapshots': {
                    snapshot_id: snapshot.to_dict()
                    for snapshot_id, snapshot in self.snapshots.items()
                }
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"{Fore.RED}Error: Failed to save rollback index: {e}{Style.RESET_ALL}")
    
    def _encode_content(self, content: str) -> str:
        """Encode content using gzip + base64"""
        compressed = gzip.compress(content.encode('utf-8'))
        return base64.b64encode(compressed).decode('ascii')
    
    def _decode_content(self, encoded: str) -> str:
        """Decode content from gzip + base64"""
        compressed = base64.b64decode(encoded.encode('ascii'))
        return gzip.decompress(compressed).decode('utf-8')
    
    def _generate_version_id(self) -> str:
        """Generate a unique version ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    def backup_file(
        self,
        file_path: str,
        operation: str = "edit",
        tags: Optional[List[str]] = None,
        description: str = ""
    ) -> Tuple[bool, str]:
        """
        Create a backup version of a file before modifying it
        
        Args:
            file_path: Path to the file to backup
            operation: Type of operation (edit, write, delete, etc.)
            tags: Optional tags for this version
            description: Optional description of the changes
        
        Returns:
            Tuple of (success, message/error)
        """
        try:
            # Read current file content
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create version
            version_id = self._generate_version_id()
            file_size = len(content.encode('utf-8'))
            
            version = FileVersion(
                version_id=version_id,
                file_path=file_path,
                timestamp=datetime.now().isoformat(),
                content_b64=self._encode_content(content),
                size_bytes=file_size,
                operation=operation,
                tags=tags or [],
                description=description
            )
            
            # Add to index
            if file_path not in self.file_versions:
                self.file_versions[file_path] = []
            self.file_versions[file_path].append(version)
            
            # Save index
            self._save_index()
            
            return True, f"Backed up {file_path} (version: {version_id})"
        
        except Exception as e:
            return False, f"Backup failed: {str(e)}"
    
    def rollback_file(
        self,
        file_path: str,
        version_id: Optional[str] = None,
        steps_back: int = 1
    ) -> Tuple[bool, str]:
        """
        Rollback a file to a previous version
        
        Args:
            file_path: Path to the file to rollback
            version_id: Specific version ID to rollback to. If None, uses steps_back.
            steps_back: Number of versions to go back (default: 1)
        
        Returns:
            Tuple of (success, message/error)
        """
        try:
            if file_path not in self.file_versions:
                return False, f"No version history found for {file_path}"
            
            versions = self.file_versions[file_path]
            if not versions:
                return False, f"No versions available for {file_path}"
            
            # Find target version
            target_version = None
            if version_id:
                target_version = next(
                    (v for v in versions if v.version_id == version_id),
                    None
                )
                if not target_version:
                    return False, f"Version {version_id} not found"
            else:
                if steps_back > len(versions):
                    return False, f"Cannot go back {steps_back} versions (only {len(versions)} available)"
                target_version = versions[-steps_back]
            
            # Restore content
            content = self._decode_content(target_version.content_b64)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, f"Rolled back {file_path} to version {target_version.version_id}"
        
        except Exception as e:
            return False, f"Rollback failed: {str(e)}"
    
    def get_version_history(
        self,
        file_path: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a file
        
        Args:
            file_path: Path to the file
            limit: Maximum number of versions to return (most recent first)
        
        Returns:
            List of version metadata (without content)
        """
        if file_path not in self.file_versions:
            return []
        
        versions = self.file_versions[file_path]
        
        # Sort by timestamp (most recent first)
        versions = sorted(versions, key=lambda v: v.timestamp, reverse=True)
        
        if limit:
            versions = versions[:limit]
        
        # Return metadata only (without content)
        return [
            {
                'version_id': v.version_id,
                'timestamp': v.timestamp,
                'operation': v.operation,
                'size_bytes': v.size_bytes,
                'tags': v.tags,
                'description': v.description
            }
            for v in versions
        ]
    
    def get_diff(
        self,
        file_path: str,
        version_id1: Optional[str] = None,
        version_id2: Optional[str] = None,
        context_lines: int = 3
    ) -> Tuple[bool, str]:
        """
        Get diff between two versions of a file
        
        Args:
            file_path: Path to the file
            version_id1: First version ID (if None, uses current file)
            version_id2: Second version ID (if None, uses previous version)
            context_lines: Number of context lines in diff
        
        Returns:
            Tuple of (success, diff_text/error)
        """
        try:
            if file_path not in self.file_versions:
                return False, f"No version history found for {file_path}"
            
            versions = self.file_versions[file_path]
            
            # Get first content
            if version_id1 is None:
                # Use current file
                if not os.path.exists(file_path):
                    return False, f"File not found: {file_path}"
                with open(file_path, 'r', encoding='utf-8') as f:
                    content1 = f.read()
                label1 = "current"
            else:
                version1 = next((v for v in versions if v.version_id == version_id1), None)
                if not version1:
                    return False, f"Version {version_id1} not found"
                content1 = self._decode_content(version1.content_b64)
                label1 = version_id1
            
            # Get second content
            if version_id2 is None:
                # Use previous version
                if len(versions) < 1:
                    return False, "No previous version available"
                version2 = versions[-1]
                content2 = self._decode_content(version2.content_b64)
                label2 = version2.version_id
            else:
                version2 = next((v for v in versions if v.version_id == version_id2), None)
                if not version2:
                    return False, f"Version {version_id2} not found"
                content2 = self._decode_content(version2.content_b64)
                label2 = version_id2
            
            # Generate diff
            diff = difflib.unified_diff(
                content2.splitlines(keepends=True),
                content1.splitlines(keepends=True),
                fromfile=f"{file_path} ({label2})",
                tofile=f"{file_path} ({label1})",
                n=context_lines
            )
            
            diff_text = ''.join(diff)
            if not diff_text:
                diff_text = "No differences found"
            
            return True, diff_text
        
        except Exception as e:
            return False, f"Diff failed: {str(e)}"
    
    def create_snapshot(
        self,
        description: str,
        file_paths: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Create a snapshot of multiple files
        
        Args:
            description: Description of the snapshot
            file_paths: List of files to include (if None, includes all tracked files)
            tags: Optional tags for this snapshot
        
        Returns:
            Tuple of (success, snapshot_id/error)
        """
        try:
            snapshot_id = self._generate_version_id()
            
            # Determine files to snapshot
            if file_paths is None:
                file_paths = list(self.file_versions.keys())
            
            # Get current version IDs for each file
            file_versions_map = {}
            for file_path in file_paths:
                if file_path in self.file_versions and self.file_versions[file_path]:
                    # Use the most recent version
                    file_versions_map[file_path] = self.file_versions[file_path][-1].version_id
            
            # Create snapshot
            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.now().isoformat(),
                description=description,
                file_versions=file_versions_map,
                tags=tags or []
            )
            
            self.snapshots[snapshot_id] = snapshot
            self._save_index()
            
            return True, snapshot_id
        
        except Exception as e:
            return False, f"Snapshot creation failed: {str(e)}"
    
    def restore_snapshot(self, snapshot_id: str) -> Tuple[bool, str]:
        """
        Restore all files from a snapshot
        
        Args:
            snapshot_id: ID of the snapshot to restore
        
        Returns:
            Tuple of (success, message/error)
        """
        try:
            if snapshot_id not in self.snapshots:
                return False, f"Snapshot {snapshot_id} not found"
            
            snapshot = self.snapshots[snapshot_id]
            restored_files = []
            failed_files = []
            
            for file_path, version_id in snapshot.file_versions.items():
                success, msg = self.rollback_file(file_path, version_id=version_id)
                if success:
                    restored_files.append(file_path)
                else:
                    failed_files.append((file_path, msg))
            
            result_msg = f"Restored snapshot {snapshot_id}:\n"
            result_msg += f"  Successfully restored: {len(restored_files)} files\n"
            
            if failed_files:
                result_msg += f"  Failed: {len(failed_files)} files\n"
                for file_path, error in failed_files[:3]:  # Show first 3 errors
                    result_msg += f"    - {file_path}: {error}\n"
            
            return len(failed_files) == 0, result_msg
        
        except Exception as e:
            return False, f"Snapshot restore failed: {str(e)}"
    
    def list_snapshots(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all snapshots
        
        Args:
            limit: Maximum number of snapshots to return (most recent first)
        
        Returns:
            List of snapshot metadata
        """
        snapshots = sorted(
            self.snapshots.values(),
            key=lambda s: s.timestamp,
            reverse=True
        )
        
        if limit:
            snapshots = snapshots[:limit]
        
        return [
            {
                'snapshot_id': s.snapshot_id,
                'timestamp': s.timestamp,
                'description': s.description,
                'file_count': len(s.file_versions),
                'tags': s.tags
            }
            for s in snapshots
        ]
    
    def cleanup_old_versions(
        self,
        keep_recent: int = 10,
        keep_tagged: bool = True
    ) -> Tuple[int, int]:
        """
        Clean up old versions to save space
        
        Args:
            keep_recent: Number of recent versions to keep per file
            keep_tagged: Whether to keep tagged versions
        
        Returns:
            Tuple of (files_cleaned, versions_removed)
        """
        files_cleaned = 0
        versions_removed = 0
        
        for file_path, versions in self.file_versions.items():
            if len(versions) <= keep_recent:
                continue
            
            # Sort by timestamp
            versions = sorted(versions, key=lambda v: v.timestamp, reverse=True)
            
            # Keep recent versions
            keep_versions = versions[:keep_recent]
            
            # Optionally keep tagged versions
            if keep_tagged:
                for v in versions[keep_recent:]:
                    if v.tags:
                        keep_versions.append(v)
            
            # Remove old versions
            removed = len(versions) - len(keep_versions)
            if removed > 0:
                self.file_versions[file_path] = keep_versions
                files_cleaned += 1
                versions_removed += removed
        
        if versions_removed > 0:
            self._save_index()
        
        return files_cleaned, versions_removed
    
    def add_tag(
        self,
        file_path: str,
        version_id: str,
        tag: str
    ) -> Tuple[bool, str]:
        """
        Add a tag to a specific version
        
        Args:
            file_path: Path to the file
            version_id: Version ID to tag
            tag: Tag to add
        
        Returns:
            Tuple of (success, message/error)
        """
        try:
            if file_path not in self.file_versions:
                return False, f"No version history found for {file_path}"
            
            version = next(
                (v for v in self.file_versions[file_path] if v.version_id == version_id),
                None
            )
            
            if not version:
                return False, f"Version {version_id} not found"
            
            if tag not in version.tags:
                version.tags.append(tag)
                self._save_index()
            
            return True, f"Tagged version {version_id} with '{tag}'"
        
        except Exception as e:
            return False, f"Tagging failed: {str(e)}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the rollback system
        
        Returns:
            Dictionary with statistics
        """
        total_files = len(self.file_versions)
        total_versions = sum(len(versions) for versions in self.file_versions.values())
        total_snapshots = len(self.snapshots)
        
        total_size = 0
        for versions in self.file_versions.values():
            for version in versions:
                total_size += version.size_bytes
        
        return {
            'total_files': total_files,
            'total_versions': total_versions,
            'total_snapshots': total_snapshots,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'storage_dir': str(self.storage_dir)
        }
