import os

# TODO: use rar for splitting files, so user can create the original file easier
def split_file(filepath, chunk_size=20 * 1024 * 1024) -> list[str]:  # 49 MB chunks
    """Splits a file into binary chunks and returns a list of part paths."""
    file_size = os.path.getsize(filepath)
    if file_size <= chunk_size:
        return [filepath]

    part_files = []
    part_num = 1
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            # Create extensions like .part001, .part002
            part_name = f"{filepath}.part{part_num:03d}"
            with open(part_name, "wb") as p:
                p.write(chunk)
            part_files.append(part_name)
            part_num += 1

    # Remove the original large file to save disk space
    # TODO: should i delete it here? single-responsibility?
    os.remove(filepath)
    return part_files
