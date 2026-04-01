from pathlib import Path

def remove_trailing_pipe(file_path: Path) -> None:
    lines = file_path.read_text().splitlines()
    cleaned = [
        line.rstrip('|') if line.endswith('|') else line
        for line in lines
    ]
    file_path.write_text('\n'.join(cleaned) + '\n')
    print(f"Cleaned {len(cleaned)} lines in {file_path.name}")

data_folder = Path("data")

for csv_file in data_folder.glob("*.csv"):
    remove_trailing_pipe(csv_file)

print("Done!")