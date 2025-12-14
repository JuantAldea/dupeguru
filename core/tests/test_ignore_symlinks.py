import os
from pathlib import Path

from core.directories import Directories
from core.fs import File


def test_symlink_ignored_by_default(tmp_path):
    p = tmp_path
    real = p / "file.txt"
    real.write_text("x")
    link = p / "link.txt"
    # create a symlink pointing to the real file
    link.symlink_to(real)

    opts = {"ignore_symlinks": True}
    d = Directories(options=opts)
    d.add_path(p)
    names = [f.name for f in d.get_files()]

    assert "file.txt" in names
    assert "link.txt" not in names


def test_symlink_included_when_option_false_and_handler_passed(tmp_path):
    p = tmp_path
    real = p / "file.txt"
    real.write_text("x")
    link = p / "link.txt"
    link.symlink_to(real)

    opts = {"ignore_symlinks": False}
    d = Directories(options=opts)
    d.add_path(p)

    # Custom fileclass that accepts symlinks pointing to existing files
    class SymlinkFile(File):
        @classmethod
        def can_handle(cls, path):
            try:
                # path can be a DirEntry or a pathlib.Path; DirEntry has no exists()
                is_link = path.is_symlink()
                try:
                    exists = os.path.exists(path.path)
                except Exception:
                    # fallback for pathlib.Path
                    exists = Path(path).exists()
                return is_link and exists
            except OSError:
                return False

    names = sorted([f.name for f in d.get_files(fileclasses=[SymlinkFile, File])])
    assert "file.txt" in names
    assert "link.txt" in names


def test_broken_symlink_skipped_even_when_option_false(tmp_path):
    p = tmp_path
    # Point the link to a non-existent target
    target = p / "nope.txt"
    link = p / "broken.txt"
    link.symlink_to(target)

    opts = {"ignore_symlinks": False}
    d = Directories(options=opts)
    d.add_path(p)

    class SymlinkFile(File):
        @classmethod
        def can_handle(cls, path):
            try:
                is_link = path.is_symlink()
                try:
                    exists = os.path.exists(path.path)
                except Exception:
                    exists = Path(path).exists()
                return is_link and exists
            except OSError:
                return False

    names = [f.name for f in d.get_files(fileclasses=[SymlinkFile, File])]
    assert "broken.txt" not in names


def test_symlinked_directory_respected(tmp_path):
    p = tmp_path
    # Create a real directory with one file
    real_dir = p / "real"
    real_dir.mkdir()
    real_file = real_dir / "inner.txt"
    real_file.write_text("content")

    # Create a symlink to that directory
    link_dir = p / "linkdir"
    # pathlib.Path.symlink_to accepts target_is_directory for Windows, safe to set
    link_dir.symlink_to(real_dir, target_is_directory=True)

    # When ignore_symlinks is True (default), we should only see the real file once
    d1 = Directories(options={"ignore_symlinks": True})
    d1.add_path(p)
    files1 = list(d1.get_files())
    # Only the file under the real directory should be returned
    assert any(f.name == "inner.txt" for f in files1)
    assert len([f for f in files1 if f.name == "inner.txt"]) == 1

    # When ignore_symlinks is False, the symlinked directory is traversed too -> two entries
    d2 = Directories(options={"ignore_symlinks": False})
    d2.add_path(p)
    files2 = list(d2.get_files())
    # We expect two entries with the same filename (one via real dir, one via symlink)
    inner_files = [f for f in files2 if f.name == "inner.txt"]
    assert len(inner_files) == 2
