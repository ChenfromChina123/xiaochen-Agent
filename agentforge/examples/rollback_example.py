"""
Example usage of the Enhanced Rollback Manager

This script demonstrates how to use the RollbackManager for:
- Backing up files before modifications
- Rolling back to previous versions
- Creating and restoring snapshots
- Viewing version history and diffs
- Managing tags and cleanup
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from xiaochen_agent_v2.core.rollback_manager import RollbackManager
from colorama import Fore, Style, init

init(autoreset=True)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")


def example_basic_rollback():
    """Example: Basic file backup and rollback"""
    print_section("Example 1: Basic File Backup and Rollback")
    
    # Initialize rollback manager
    rm = RollbackManager()
    
    # Create a test file
    test_file = "test_rollback_file.txt"
    
    # Version 1
    with open(test_file, 'w') as f:
        f.write("Version 1: Initial content\n")
    print(f"✓ Created {test_file} with initial content")
    
    # Backup before modifying
    success, msg = rm.backup_file(test_file, operation="create", description="Initial version")
    print(f"✓ {msg}")
    
    # Version 2
    with open(test_file, 'a') as f:
        f.write("Version 2: Added some text\n")
    print(f"✓ Modified {test_file}")
    
    rm.backup_file(test_file, operation="edit", description="Added text")
    
    # Version 3
    with open(test_file, 'a') as f:
        f.write("Version 3: Added more text\n")
    print(f"✓ Modified {test_file} again")
    
    rm.backup_file(test_file, operation="edit", description="Added more text")
    
    # Show current content
    with open(test_file, 'r') as f:
        print(f"\n{Fore.YELLOW}Current content:{Style.RESET_ALL}")
        print(f.read())
    
    # Rollback 1 version
    print(f"{Fore.GREEN}Rolling back 1 version...{Style.RESET_ALL}")
    success, msg = rm.rollback_file(test_file, steps_back=1)
    print(f"✓ {msg}")
    
    with open(test_file, 'r') as f:
        print(f"\n{Fore.YELLOW}Content after rollback:{Style.RESET_ALL}")
        print(f.read())
    
    # Cleanup
    os.remove(test_file)
    print(f"\n✓ Cleaned up test file")


def example_version_history():
    """Example: View version history"""
    print_section("Example 2: Version History")
    
    rm = RollbackManager()
    test_file = "test_history.txt"
    
    # Create multiple versions
    for i in range(1, 6):
        with open(test_file, 'w') as f:
            f.write(f"Version {i} content\n" * i)
        
        tags = ["important"] if i == 3 else []
        rm.backup_file(
            test_file,
            operation="edit",
            tags=tags,
            description=f"Version {i} update"
        )
    
    # Get version history
    history = rm.get_version_history(test_file, limit=10)
    
    print(f"{Fore.YELLOW}Version history for {test_file}:{Style.RESET_ALL}\n")
    print(f"{'Version ID':<20} {'Timestamp':<25} {'Operation':<10} {'Size':<10} {'Tags'}")
    print("-" * 90)
    
    for v in history:
        tags_str = ', '.join(v['tags']) if v['tags'] else '-'
        print(f"{v['version_id']:<20} {v['timestamp']:<25} {v['operation']:<10} {v['size_bytes']:<10} {tags_str}")
    
    # Cleanup
    os.remove(test_file)
    print(f"\n✓ Cleaned up test file")


def example_diff_comparison():
    """Example: Compare versions with diff"""
    print_section("Example 3: Diff Comparison")
    
    rm = RollbackManager()
    test_file = "test_diff.py"
    
    # Version 1
    with open(test_file, 'w') as f:
        f.write("""def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye!")
""")
    rm.backup_file(test_file, description="Initial functions")
    
    # Version 2
    with open(test_file, 'w') as f:
        f.write("""def hello(name="World"):
    print(f"Hello, {name}!")

def goodbye(name="World"):
    print(f"Goodbye, {name}!")

def welcome():
    print("Welcome!")
""")
    rm.backup_file(test_file, description="Added parameters and new function")
    
    # Get diff
    success, diff = rm.get_diff(test_file)
    
    if success:
        print(f"{Fore.YELLOW}Diff between current and previous version:{Style.RESET_ALL}\n")
        print(diff)
    
    # Cleanup
    os.remove(test_file)
    print(f"\n✓ Cleaned up test file")


def example_snapshots():
    """Example: Create and restore snapshots"""
    print_section("Example 4: Snapshots")
    
    rm = RollbackManager()
    
    # Create multiple test files
    files = {
        "config.json": '{"version": "1.0", "debug": true}',
        "data.txt": "Important data\nLine 2\nLine 3",
        "script.py": "print('Hello')\n"
    }
    
    print("Creating initial files...")
    for filename, content in files.items():
        with open(filename, 'w') as f:
            f.write(content)
        rm.backup_file(filename, operation="create")
    print("✓ Files created and backed up")
    
    # Create snapshot
    success, snapshot_id = rm.create_snapshot(
        description="Initial project state",
        tags=["milestone", "v1.0"]
    )
    print(f"✓ Created snapshot: {snapshot_id}")
    
    # Modify files
    print("\nModifying files...")
    with open("config.json", 'w') as f:
        f.write('{"version": "2.0", "debug": false}')
    with open("data.txt", 'w') as f:
        f.write("Modified data\nNew content")
    print("✓ Files modified")
    
    # List snapshots
    snapshots = rm.list_snapshots()
    print(f"\n{Fore.YELLOW}Available snapshots:{Style.RESET_ALL}\n")
    for s in snapshots:
        print(f"  {s['snapshot_id']}: {s['description']}")
        print(f"    Files: {s['file_count']}, Tags: {', '.join(s['tags'])}")
    
    # Restore snapshot
    print(f"\n{Fore.GREEN}Restoring snapshot...{Style.RESET_ALL}")
    success, msg = rm.restore_snapshot(snapshot_id)
    print(msg)
    
    # Verify restoration
    with open("config.json", 'r') as f:
        content = f.read()
        print(f"\n{Fore.YELLOW}Restored config.json:{Style.RESET_ALL}")
        print(content)
    
    # Cleanup
    for filename in files.keys():
        if os.path.exists(filename):
            os.remove(filename)
    print(f"\n✓ Cleaned up test files")


def example_tagging():
    """Example: Tag important versions"""
    print_section("Example 5: Version Tagging")
    
    rm = RollbackManager()
    test_file = "important_file.txt"
    
    # Create versions
    for i in range(1, 4):
        with open(test_file, 'w') as f:
            f.write(f"Version {i}\n")
        rm.backup_file(test_file, description=f"Update {i}")
    
    # Get version history
    history = rm.get_version_history(test_file)
    
    # Tag the middle version as stable
    if len(history) >= 2:
        version_id = history[1]['version_id']
        success, msg = rm.add_tag(test_file, version_id, "stable")
        print(f"✓ {msg}")
        
        success, msg = rm.add_tag(test_file, version_id, "tested")
        print(f"✓ {msg}")
    
    # Show updated history
    history = rm.get_version_history(test_file)
    print(f"\n{Fore.YELLOW}Version history with tags:{Style.RESET_ALL}\n")
    for v in history:
        tags = f" [{', '.join(v['tags'])}]" if v['tags'] else ""
        print(f"  {v['version_id']}: {v['description']}{tags}")
    
    # Cleanup
    os.remove(test_file)
    print(f"\n✓ Cleaned up test file")


def example_statistics():
    """Example: View system statistics"""
    print_section("Example 6: System Statistics")
    
    rm = RollbackManager()
    
    # Create some test data
    for i in range(3):
        test_file = f"test_{i}.txt"
        for j in range(5):
            with open(test_file, 'w') as f:
                f.write(f"Content {j}\n" * 100)
            rm.backup_file(test_file)
        os.remove(test_file)
    
    # Get statistics
    stats = rm.get_statistics()
    
    print(f"{Fore.YELLOW}Rollback System Statistics:{Style.RESET_ALL}\n")
    print(f"  Total files tracked: {stats['total_files']}")
    print(f"  Total versions: {stats['total_versions']}")
    print(f"  Total snapshots: {stats['total_snapshots']}")
    print(f"  Total storage size: {stats['total_size_mb']} MB")
    print(f"  Storage directory: {stats['storage_dir']}")


def example_cleanup():
    """Example: Cleanup old versions"""
    print_section("Example 7: Cleanup Old Versions")
    
    rm = RollbackManager()
    test_file = "test_cleanup.txt"
    
    # Create many versions
    print("Creating 20 versions...")
    for i in range(20):
        with open(test_file, 'w') as f:
            f.write(f"Version {i}\n" * 10)
        
        tags = ["important"] if i % 5 == 0 else []
        rm.backup_file(test_file, tags=tags)
    
    print(f"✓ Created 20 versions")
    
    # Check before cleanup
    history = rm.get_version_history(test_file)
    print(f"Versions before cleanup: {len(history)}")
    
    # Cleanup (keep 5 recent, keep tagged)
    files_cleaned, versions_removed = rm.cleanup_old_versions(
        keep_recent=5,
        keep_tagged=True
    )
    
    print(f"\n{Fore.GREEN}Cleanup results:{Style.RESET_ALL}")
    print(f"  Files cleaned: {files_cleaned}")
    print(f"  Versions removed: {versions_removed}")
    
    # Check after cleanup
    history = rm.get_version_history(test_file)
    print(f"  Versions after cleanup: {len(history)}")
    print(f"  (5 recent + tagged versions were kept)")
    
    # Cleanup
    os.remove(test_file)
    print(f"\n✓ Cleaned up test file")


def main():
    """Run all examples"""
    print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Enhanced Rollback Manager - Examples{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
    
    examples = [
        ("Basic Rollback", example_basic_rollback),
        ("Version History", example_version_history),
        ("Diff Comparison", example_diff_comparison),
        ("Snapshots", example_snapshots),
        ("Version Tagging", example_tagging),
        ("Statistics", example_statistics),
        ("Cleanup", example_cleanup)
    ]
    
    print(f"\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print(f"  0. Run all examples")
    
    try:
        choice = input(f"\n{Fore.GREEN}Select example (0-{len(examples)}): {Style.RESET_ALL}").strip()
        
        if choice == "0":
            for name, func in examples:
                func()
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            examples[int(choice) - 1][1]()
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
    
    print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Examples completed{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
