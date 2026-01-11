"""
Terminal Output Manager

This module manages detailed terminal output storage and retrieval.
Allows users to view full terminal output even when it's truncated in the chat.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style


class TerminalOutputRecord:
    """Represents a single terminal command execution record"""
    
    def __init__(
        self,
        record_id: str,
        command: str,
        cwd: str,
        timestamp: str,
        exit_code: Optional[int],
        stdout: str,
        stderr: str,
        duration_ms: Optional[int] = None
    ):
        """
        Initialize a terminal output record
        
        Args:
            record_id: Unique identifier for this execution
            command: The command that was executed
            cwd: Working directory
            timestamp: ISO format timestamp
            exit_code: Command exit code
            stdout: Standard output
            stderr: Standard error
            duration_ms: Execution duration in milliseconds
        """
        self.record_id = record_id
        self.command = command
        self.cwd = cwd
        self.timestamp = timestamp
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'record_id': self.record_id,
            'command': self.command,
            'cwd': self.cwd,
            'timestamp': self.timestamp,
            'exit_code': self.exit_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'duration_ms': self.duration_ms,
            'stdout_length': len(self.stdout),
            'stderr_length': len(self.stderr)
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'TerminalOutputRecord':
        """Create record from dictionary"""
        return TerminalOutputRecord(
            record_id=data['record_id'],
            command=data['command'],
            cwd=data['cwd'],
            timestamp=data['timestamp'],
            exit_code=data['exit_code'],
            stdout=data.get('stdout', ''),
            stderr=data.get('stderr', ''),
            duration_ms=data.get('duration_ms')
        )


class TerminalOutputManager:
    """
    Manages storage and retrieval of detailed terminal outputs
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the terminal output manager
        
        Args:
            storage_dir: Directory to store terminal outputs. If None, uses default location.
        """
        if storage_dir is None:
            from ..utils.logs import get_logs_root
            storage_dir = os.path.join(get_logs_root(), "terminal_outputs")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Index file for quick lookups
        self.index_file = self.storage_dir / "index.json"
        
        # In-memory cache of recent records
        self.recent_records: List[TerminalOutputRecord] = []
        self.max_recent = 20  # Keep last 20 in memory
        
        # Load index
        self._load_index()
    
    def _load_index(self) -> None:
        """Load the index from disk"""
        if not self.index_file.exists():
            return
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load recent records
            for record_data in data.get('recent_records', [])[-self.max_recent:]:
                self.recent_records.append(TerminalOutputRecord.from_dict(record_data))
        
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Failed to load terminal output index: {e}{Style.RESET_ALL}")
    
    def _save_index(self) -> None:
        """Save the index to disk"""
        try:
            data = {
                'recent_records': [r.to_dict() for r in self.recent_records],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"{Fore.RED}Error: Failed to save terminal output index: {e}{Style.RESET_ALL}")
    
    def _get_record_file_path(self, record_id: str) -> Path:
        """Get the file path for a specific record"""
        # Organize by date
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = self.storage_dir / date_str
        date_dir.mkdir(exist_ok=True)
        return date_dir / f"{record_id}.json"
    
    def save_output(
        self,
        record_id: str,
        command: str,
        cwd: str,
        exit_code: Optional[int],
        stdout: str,
        stderr: str,
        duration_ms: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Save terminal output to storage
        
        Args:
            record_id: Unique identifier (e.g., terminal ID)
            command: The executed command
            cwd: Working directory
            exit_code: Command exit code
            stdout: Standard output
            stderr: Standard error
            duration_ms: Execution duration in milliseconds
        
        Returns:
            Tuple of (success, message/error)
        """
        try:
            record = TerminalOutputRecord(
                record_id=record_id,
                command=command,
                cwd=cwd,
                timestamp=datetime.now().isoformat(),
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms
            )
            
            # Save to individual file
            file_path = self._get_record_file_path(record_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(record.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Update in-memory cache
            self.recent_records.append(record)
            if len(self.recent_records) > self.max_recent:
                self.recent_records.pop(0)
            
            # Save index
            self._save_index()
            
            return True, f"Saved terminal output: {record_id}"
        
        except Exception as e:
            return False, f"Failed to save terminal output: {str(e)}"
    
    def get_output(self, record_id: str) -> Tuple[bool, Optional[TerminalOutputRecord], str]:
        """
        Retrieve terminal output by ID
        
        Args:
            record_id: The record ID to retrieve
        
        Returns:
            Tuple of (success, record/None, message/error)
        """
        try:
            # Check in-memory cache first
            for record in reversed(self.recent_records):
                if record.record_id == record_id:
                    return True, record, "Found in cache"
            
            # Search in storage
            # Try today first
            today = datetime.now().strftime("%Y%m%d")
            file_path = self.storage_dir / today / f"{record_id}.json"
            
            if not file_path.exists():
                # Search in recent days (last 7 days)
                from datetime import timedelta
                for days_back in range(1, 8):
                    date = datetime.now() - timedelta(days=days_back)
                    date_str = date.strftime("%Y%m%d")
                    file_path = self.storage_dir / date_str / f"{record_id}.json"
                    if file_path.exists():
                        break
                else:
                    return False, None, f"Record {record_id} not found"
            
            # Load from file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            record = TerminalOutputRecord.from_dict(data)
            return True, record, "Found in storage"
        
        except Exception as e:
            return False, None, f"Error retrieving record: {str(e)}"
    
    def list_recent(self, limit: int = 10) -> List[Dict]:
        """
        List recent terminal outputs
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of record summaries (without full stdout/stderr)
        """
        records = self.recent_records[-limit:]
        records.reverse()  # Most recent first
        
        return [
            {
                'record_id': r.record_id,
                'command': r.command[:100] + '...' if len(r.command) > 100 else r.command,
                'timestamp': r.timestamp,
                'exit_code': r.exit_code,
                'cwd': r.cwd,
                'stdout_length': len(r.stdout),
                'stderr_length': len(r.stderr),
                'truncated': len(r.stdout) > 2000 or len(r.stderr) > 2000
            }
            for r in records
        ]
    
    def format_output_display(self, record: TerminalOutputRecord, max_lines: Optional[int] = None) -> str:
        """
        Format a record for display
        
        Args:
            record: The record to format
            max_lines: Maximum number of lines to display (None = all)
        
        Returns:
            Formatted string for display
        """
        lines = []
        
        # Header
        lines.append(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}Terminal Output Details{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        
        # Metadata
        lines.append(f"{Fore.YELLOW}Record ID:{Style.RESET_ALL} {record.record_id}")
        lines.append(f"{Fore.YELLOW}Command:{Style.RESET_ALL} {record.command}")
        lines.append(f"{Fore.YELLOW}Working Directory:{Style.RESET_ALL} {record.cwd}")
        lines.append(f"{Fore.YELLOW}Timestamp:{Style.RESET_ALL} {record.timestamp}")
        
        if record.duration_ms is not None:
            duration_str = f"{record.duration_ms}ms"
            if record.duration_ms >= 1000:
                duration_str = f"{record.duration_ms / 1000:.2f}s"
            lines.append(f"{Fore.YELLOW}Duration:{Style.RESET_ALL} {duration_str}")
        
        exit_color = Fore.GREEN if record.exit_code == 0 else Fore.RED
        lines.append(f"{Fore.YELLOW}Exit Code:{Style.RESET_ALL} {exit_color}{record.exit_code}{Style.RESET_ALL}")
        
        # Stdout
        if record.stdout:
            lines.append(f"\n{Fore.GREEN}Standard Output:{Style.RESET_ALL}")
            lines.append(f"{Fore.GREEN}{'-' * 60}{Style.RESET_ALL}")
            
            stdout_lines = record.stdout.splitlines()
            if max_lines and len(stdout_lines) > max_lines:
                lines.extend(stdout_lines[:max_lines])
                lines.append(f"{Fore.BLACK}{Style.BRIGHT}... ({len(stdout_lines) - max_lines} more lines){Style.RESET_ALL}")
            else:
                lines.extend(stdout_lines)
        else:
            lines.append(f"\n{Fore.BLACK}{Style.BRIGHT}(No standard output){Style.RESET_ALL}")
        
        # Stderr
        if record.stderr:
            lines.append(f"\n{Fore.RED}Standard Error:{Style.RESET_ALL}")
            lines.append(f"{Fore.RED}{'-' * 60}{Style.RESET_ALL}")
            
            stderr_lines = record.stderr.splitlines()
            if max_lines and len(stderr_lines) > max_lines:
                lines.extend(stderr_lines[:max_lines])
                lines.append(f"{Fore.BLACK}{Style.BRIGHT}... ({len(stderr_lines) - max_lines} more lines){Style.RESET_ALL}")
            else:
                lines.extend(stderr_lines)
        
        lines.append(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        
        return '\n'.join(lines)
    
    def cleanup_old_records(self, days_to_keep: int = 7) -> Tuple[int, int]:
        """
        Clean up old terminal output records
        
        Args:
            days_to_keep: Number of days to keep records
        
        Returns:
            Tuple of (directories_removed, files_removed)
        """
        from datetime import timedelta
        
        dirs_removed = 0
        files_removed = 0
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            for date_dir in self.storage_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                    if dir_date < cutoff_date:
                        # Remove all files in this directory
                        file_count = 0
                        for file_path in date_dir.glob("*.json"):
                            file_path.unlink()
                            file_count += 1
                        
                        # Remove the directory
                        date_dir.rmdir()
                        dirs_removed += 1
                        files_removed += file_count
                
                except ValueError:
                    # Invalid directory name format, skip
                    continue
        
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Cleanup encountered error: {e}{Style.RESET_ALL}")
        
        return dirs_removed, files_removed
    
    def get_storage_stats(self) -> Dict:
        """
        Get statistics about stored terminal outputs
        
        Returns:
            Dictionary with storage statistics
        """
        total_files = 0
        total_size = 0
        date_dirs = 0
        
        try:
            for date_dir in self.storage_dir.iterdir():
                if date_dir.is_dir():
                    date_dirs += 1
                    for file_path in date_dir.glob("*.json"):
                        total_files += 1
                        total_size += file_path.stat().st_size
        
        except Exception:
            pass
        
        return {
            'total_records': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'date_directories': date_dirs,
            'recent_records_cached': len(self.recent_records),
            'storage_dir': str(self.storage_dir)
        }
