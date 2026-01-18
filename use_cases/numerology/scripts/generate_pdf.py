#!/usr/bin/env python3
"""
PDF Generation Script for Research Paper

Renders the Quarto research paper document to PDF format.
Handles figure generation, data paths, and Quarto rendering.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import json

class PDFGenerator:
    """
    Generates PDF from Quarto research paper document.
    """

    def __init__(self, paper_path: Optional[str] = None, output_dir: Optional[str] = None):
        """
        Initialize PDF generator.

        Args:
            paper_path: Path to the Quarto document (optional, auto-detect)
            output_dir: Output directory for generated PDF (optional)
        """
        # Auto-detect paths
        if paper_path is None:
            paper_path = os.path.join(os.path.dirname(__file__), '..', 'research_paper', 'numerology_astrology_correlation.qmd')

        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'research_paper')

        self.paper_path = os.path.abspath(paper_path)
        self.output_dir = os.path.abspath(output_dir)
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Check if Quarto is available
        self.quarto_available = self._check_quarto_availability()

    def _check_quarto_availability(self) -> bool:
        """Check if Quarto is installed and available."""
        try:
            result = subprocess.run(['quarto', '--version'],
                                  capture_output=True, text=True, check=True)
            version = result.stdout.strip()
            print(f"Quarto version {version} found")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: Quarto not found. Please install Quarto to generate PDFs.")
            print("Visit: https://quarto.org/docs/get-started/")
            return False

    def check_dependencies(self) -> bool:
        """
        Check if all required dependencies are available.

        Returns:
            True if all dependencies are available
        """
        dependencies_ok = True

        # Check Python dependencies
        required_packages = ['pandas', 'matplotlib', 'seaborn', 'plotly', 'scipy', 'numpy']
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            print(f"Warning: Missing Python packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            dependencies_ok = False

        # Check data files
        data_files = [
            'data/processed/temporal_analysis_5years.csv',
            'data/processed/correlation_analysis_20260113_083901.json'
        ]

        for data_file in data_files:
            full_path = os.path.join(self.project_root, data_file)
            if not os.path.exists(full_path):
                print(f"Warning: Required data file not found: {data_file}")
                dependencies_ok = False

        # Check Quarto document
        if not os.path.exists(self.paper_path):
            print(f"Error: Quarto document not found: {self.paper_path}")
            dependencies_ok = False

        return dependencies_ok

    def prepare_data_links(self) -> None:
        """
        Prepare data file links for the research paper.
        Copy or link data files to the research paper directory.
        """
        data_dir = os.path.join(self.output_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Copy data files to research paper directory
        data_files = [
            ('data/processed/temporal_analysis_5years.csv', 'temporal_analysis_5years.csv'),
            ('data/processed/correlation_analysis_20260113_083901.json', 'correlation_analysis.json')
        ]

        for src_rel, dst_name in data_files:
            src_path = os.path.join(self.project_root, src_rel)
            dst_path = os.path.join(data_dir, dst_name)

            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                print(f"Copied {src_rel} to research paper data directory")
            else:
                print(f"Warning: Source data file not found: {src_rel}")

    def generate_figures(self) -> None:
        """
        Generate figures for the research paper.
        This runs the Python code embedded in the Quarto document.
        """
        print("Generating figures for research paper...")

        # Import the visualization functions
        sys.path.insert(0, os.path.join(self.project_root, 'src'))

        try:
            from vedic_astrology_core.visualization import (
                plot_temporal_support
            )

            # Load data
            data_path = os.path.join(self.project_root, 'data', 'processed', 'temporal_analysis_5years.csv')

            if not os.path.exists(data_path):
                print("Error: Temporal data file not found for figure generation")
                return

            # Create figures directory
            figures_dir = os.path.join(self.output_dir, 'figures')
            os.makedirs(figures_dir, exist_ok=True)

            print("Generating planet comparison figure...")
            # Generate Mars comparison (first 6 months for clarity)
            import pandas as pd
            import matplotlib.pyplot as plt
            df = pd.read_csv(data_path)
            plot_data = df.head(180)  # 6 months

            from vedic_astrology_core.config import Planet
            fig = plot_numerology_vs_astrology(
                plot_data, Planet.MARS, use_plotly=False,
                save_path=os.path.join(figures_dir, 'mars_comparison.png')
            )
            plt.close('all')  # Clean up matplotlib figures

            print("Generating moon movement figure...")
            # Generate moon movement analysis (first 3 months)
            moon_data = df.head(90)
            fig = plot_moon_movement_highlight(
                moon_data, use_plotly=False,
                save_path=os.path.join(figures_dir, 'moon_movement.png')
            )
            plt.close('all')

            print("Generating correlation analysis figures...")
            # Generate correlation analysis (first year for manageability)
            corr_data = df.head(365)
            fig = plot_correlation_analysis(
                corr_data, use_plotly=False,
                save_path=os.path.join(figures_dir, 'correlation_analysis.png')
            )
            plt.close('all')

            print("Figure generation complete")

        except Exception as e:
            print(f"Warning: Figure generation failed: {e}")
            print("PDF will be generated with placeholder figures or inline plots")

    def render_pdf(self) -> Optional[str]:
        """
        Render the Quarto document to PDF.

        Returns:
            Path to generated PDF file, or None if failed
        """
        if not self.quarto_available:
            print("Error: Quarto not available for PDF generation")
            return None

        print("Rendering PDF with Quarto...")

        # Run Quarto from the output directory
        original_cwd = os.getcwd()

        try:
            os.chdir(self.output_dir)

            # Run Quarto render
            cmd = [
                'quarto', 'render', os.path.basename(self.paper_path),
                '--to', 'pdf'
            ]

            print(f"Running from {self.output_dir}: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Check for successful rendering
            pdf_filename = os.path.basename(self.paper_path).replace('.qmd', '.pdf')
            pdf_path = os.path.join(self.output_dir, pdf_filename)

            if os.path.exists(pdf_path):
                print(f"PDF generated successfully: {pdf_path}")
                return pdf_path
            else:
                print("Error: PDF file not found after rendering")
                print("Quarto stdout:", result.stdout)
                if result.stderr:
                    print("Quarto stderr:", result.stderr)
                return None

        except subprocess.CalledProcessError as e:
            print(f"Error rendering PDF: {e}")
            print("stdout:", e.stdout)
            print("stderr:", e.stderr)
            return None

        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    def generate_pdf(self) -> Optional[str]:
        """
        Complete PDF generation pipeline.

        Returns:
            Path to generated PDF file, or None if failed
        """
        print("Starting PDF generation pipeline...")
        print("=" * 50)

        # Check dependencies
        if not self.check_dependencies():
            print("Error: Dependencies not satisfied. Cannot generate PDF.")
            return None

        # Prepare data
        print("1. Preparing data files...")
        self.prepare_data_links()

        # Generate figures
        print("2. Generating figures...")
        self.generate_figures()

        # Render PDF
        print("3. Rendering PDF...")
        pdf_path = self.render_pdf()

        if pdf_path:
            print("=" * 50)
            print("PDF GENERATION COMPLETE")
            print("=" * 50)
            print(f"PDF saved to: {pdf_path}")

            # Print file size
            if os.path.exists(pdf_path):
                size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                print(".2f")
        else:
            print("Error: PDF generation failed")

        return pdf_path

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files generated during PDF creation."""
        # Remove copied data files (keep originals)
        data_dir = os.path.join(self.output_dir, 'data')
        if os.path.exists(data_dir):
            for file in os.listdir(data_dir):
                if file.endswith(('.csv', '.json')):
                    os.remove(os.path.join(data_dir, file))

        # Clean up Quarto cache and temporary files
        cache_dirs = ['.quarto', '_book']
        for cache_dir in cache_dirs:
            cache_path = os.path.join(self.output_dir, cache_dir)
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path, ignore_errors=True)


def main():
    """Main execution function."""
    print("Research Paper PDF Generator")
    print("=" * 40)

    # Initialize generator
    generator = PDFGenerator()

    # Generate PDF
    pdf_path = generator.generate_pdf()

    if pdf_path:
        print(f"\nSuccess! Research paper PDF generated at: {pdf_path}")

        # Offer cleanup
        cleanup = input("Clean up temporary files? (y/n): ").lower().strip()
        if cleanup == 'y':
            generator.cleanup_temp_files()
            print("Temporary files cleaned up")
    else:
        print("\nPDF generation failed. Check error messages above.")
        print("\nTroubleshooting:")
        print("1. Ensure Quarto is installed: https://quarto.org/docs/get-started/")
        print("2. Install required Python packages: pip install pandas matplotlib seaborn plotly scipy numpy")
        print("3. Check that data files exist in data/processed/")
        print("4. Verify Quarto document exists: research_paper/numerology_astrology_correlation.qmd")


if __name__ == "__main__":
    main()