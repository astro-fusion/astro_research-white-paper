#!/usr/bin/env python3
"""
Fallback script to generate research manuscripts locally.
This script generates PDF, DOCX, and HTML versions of the research manuscript
and stores them in assets/releases/ for fallback access.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def generate_research_data():
    """Generate dynamic research content for the manuscript."""
    print("Generating dynamic research data...")

    script = """
from vedic_astrology_core import create_birth_chart
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import json
from datetime import datetime

# Add numerology path
sys.path.insert(0, 'use_cases/numerology/src')

try:
    from numerology.calculator import calculate_complete_numerology

    # Default birth data
    birth_date = '1984-08-27'
    birth_time = '10:30'
    latitude = 28.6139
    longitude = 77.1025

    print(f'Generating analysis for: {birth_date} {birth_time}')

    # Create astrology chart
    chart = create_birth_chart(birth_date, birth_time, latitude, longitude)

    # Calculate numerology
    numerology = calculate_complete_numerology(
        datetime.strptime(birth_date, '%Y-%m-%d').date(),
        datetime.strptime(birth_time, '%H:%M').time(),
        latitude,
        longitude
    )

    # Get dignity scores
    mars_dignity = chart.score_dignity('MARS')
    venus_dignity = chart.score_dignity('VENUS')

    # Create results file
    with open('research_results.json', 'w') as f:
        json.dump({
            'birth_data': {
                'date': birth_date,
                'time': birth_time,
                'latitude': latitude,
                'longitude': longitude
            },
            'numerology': numerology,
            'astrology': {
                'mars_dignity': mars_dignity,
                'venus_dignity': venus_dignity,
                'ascendant': chart.chart.ascendant['sign_name'] if isinstance(chart.chart.ascendant, dict) else str(chart.chart.ascendant)
            },
            'support_analysis': {
                'mars_score': mars_dignity['score'],
                'venus_score': venus_dignity['score'],
                'mars_type': mars_dignity['dignity_type'],
                'venus_type': venus_dignity['dignity_type']
            }
        }, f, indent=2, default=str)

    print('Research data generated successfully')

except Exception as e:
    print(f'Error generating research data: {e}')
    sys.exit(1)
"""

    run_command([sys.executable, "-c", script])

def copy_research_data():
    """Copy research data to manuscript directory."""
    print("Copying research data to manuscript directory...")

    src = "research_results.json"
    dst = "use_cases/numerology/manuscripts/research_results.json"

    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Copied {src} to {dst}")
    else:
        print(f"Warning: {src} not found")

def render_manuscripts():
    """Render manuscripts in different formats."""
    manuscript_dir = Path("use_cases/numerology/manuscripts")

    # Ensure we're in the manuscript directory
    os.chdir(manuscript_dir)

    formats = [
        ("pdf", ["quarto", "render", "manuscript.qmd", "--to", "pdf", "--pdf-engine", "lualatex"]),
        ("docx", ["quarto", "render", "manuscript.qmd", "--to", "docx"]),
        ("html", ["quarto", "render", "manuscript.qmd", "--to", "html"])
    ]

    generated_files = []

    for format_name, cmd in formats:
        print(f"Rendering {format_name.upper()}...")
        try:
            run_command(cmd)

            # Check what files were created
            print(f"Checking for {format_name} files after render...")
            if format_name == "html":
                # HTML creates index.html
                book_file = Path("_book/index.html")
                print(f"Looking for HTML: {book_file} (exists: {book_file.exists()})")
                if book_file.exists():
                    generated_files.append((format_name, "_book/index.html"))
            else:
                # PDF and DOCX create manuscript.{format}
                book_file = Path(f"_book/manuscript.{format_name}")
                print(f"Looking for {format_name.upper()}: {book_file} (exists: {book_file.exists()})")
                if book_file.exists():
                    generated_files.append((format_name, f"_book/manuscript.{format_name}"))
                else:
                    # Try to find any file with the extension in _book
                    found_files = list(Path("_book").glob(f"*.{format_name}"))
                    print(f"Found {format_name} files: {found_files}")
                    if found_files:
                        for found_file in found_files:
                            rel_path = str(found_file.relative_to(Path(".")))
                            generated_files.append((format_name, rel_path))

        except Exception as e:
            print(f"Failed to render {format_name}: {e}")

    # Copy files to assets before changing directory
    assets_dir = Path("../../../assets/releases")
    assets_dir.mkdir(parents=True, exist_ok=True)

    copied_files = []

    for format_name, file_path in generated_files:
        src = Path(file_path)
        if src.exists():
            # Create a timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst_name = f"vedic-numerology-research-manuscript-{timestamp}.{format_name}"
            dst = assets_dir / dst_name

            shutil.copy2(src, dst)
            print(f"Copied {src} -> {dst}")

            # Also create a latest version
            latest_dst = assets_dir / f"vedic-numerology-research-manuscript.{format_name}"
            shutil.copy2(src, latest_dst)
            print(f"Created latest version: {latest_dst}")

            copied_files.append((format_name, str(dst.relative_to(Path("../../")))))
        else:
            print(f"Warning: {src} not found")

    # Go back to root
    os.chdir("../..")

    return copied_files

# copy_to_assets function removed - now handled in render_manuscripts

def create_download_links():
    """Create a download links file."""
    assets_dir = Path("assets/releases")  # Back in root directory
    assets_dir.mkdir(parents=True, exist_ok=True)
    links_file = assets_dir / "DOWNLOAD_LINKS.md"

    print("Creating download links file...")

    content = "# Vedic Numerology-Astrology Research Manuscript Downloads\n\n"
    content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # Find latest files
    latest_files = {}
    for file in assets_dir.glob("vedic-numerology-research-manuscript.*"):
        if file.suffix in ['.pdf', '.docx', '.html']:
            latest_files[file.suffix[1:]] = file

    if latest_files:
        content += "## Latest Versions\n\n"
        for format_name, file_path in latest_files.items():
            content += f"- **{format_name.upper()}**: [{file_path.name}](./{file_path.name})\n"

    content += "\n## All Versions\n\n"
    files_by_format = {}
    for file in sorted(assets_dir.glob("vedic-numerology-research-manuscript-*.{pdf,docx,html}")):
        format_name = file.suffix[1:]
        if format_name not in files_by_format:
            files_by_format[format_name] = []
        files_by_format[format_name].append(file)

    for format_name, files in files_by_format.items():
        content += f"### {format_name.upper()} Files\n"
        for file in sorted(files, reverse=True):
            timestamp = file.stem.split('-')[-1]  # Extract timestamp from filename
            content += f"- {timestamp}: [{file.name}](./{file.name})\n"
        content += "\n"

    content += "## Notes\n\n"
    content += "- These are locally generated fallback versions\n"
    content += "- For the latest automated versions, check GitHub Actions artifacts\n"
    content += "- Files are generated using Quarto with dynamic research data\n"

    with open(links_file, 'w') as f:
        f.write(content)

    print(f"Created {links_file}")

def main():
    """Main function to generate all assets."""
    print("=== Vedic Numerology-Astrology Asset Generation ===\n")

    # Ensure we're in the project root
    os.chdir(Path(__file__).parent)

    try:
        # Generate research data
        generate_research_data()

        # Copy research data
        copy_research_data()

        # Render manuscripts and copy to assets
        generated_files = render_manuscripts()

        # Create download links
        create_download_links()

        print("\n✅ Asset generation completed successfully!")
        print("Files available in: assets/releases/")

        # List generated files
        assets_dir = Path("assets/releases")
        if assets_dir.exists():
            print("\nGenerated files:")
            for file in sorted(assets_dir.glob("*")):
                if file.is_file():
                    print(f"  - {file.name}")

    except Exception as e:
        print(f"\n❌ Asset generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()