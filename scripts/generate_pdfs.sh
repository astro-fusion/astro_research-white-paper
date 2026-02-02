#!/bin/bash
set -e

# Create pdfs directory if it doesn't exist
mkdir -p pdfs

echo "Starting PDF Generation..."

# Generate Python Artifacts first
echo "Generating Python Artifacts (Plots & Tables)..."
python3 src/generate_artifacts.py || { echo "❌ Stats/Artifact generation failed"; exit 1; }

# Function to render and move
render_and_move() {
    local source=$1
    local output_name=$2
    local output_dir="pdfs"
    
    echo "Rendering $output_name from $source..."
    quarto render "$source" --to pdf -o "$output_name"
    
    # Move the generated PDF to pdfs folder
    # Note: quarto output path behavior might vary, it usually outputs to CWD or next to source.
    # We specified -o, so it should be in CWD if no path given, or we can just move it.
    
        if [ -f "$output_name" ]; then
            mv "$output_name" "$output_dir/"
            echo "✅ Moved $output_name to $output_dir/"
        elif [ -f "_site/$output_name" ]; then
            mv "_site/$output_name" "$output_dir/"
            echo "✅ Moved $output_name from _site/ to $output_dir/"
        else
            echo "⚠️  Could not find $output_name in current directory or _site/. Checking next to source..."
            # Fallback check
            local source_dir=$(dirname "$source")
            if [ -f "$source_dir/$output_name" ]; then
                 mv "$source_dir/$output_name" "$output_dir/"
                 echo "✅ Moved $output_name from $source_dir to $output_dir/"
            else
                 echo "❌ Failed to generate $output_name"
                 # List _site just in case
                 ls -la _site/ || true
                 exit 1
            fi
        fi
}

# 1. Master Consolidated Paper
render_and_move "docs/research/VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.qmd" "VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.pdf"

# 2. Track 1
render_and_move "docs/research/track_1_numerology_vs_astrology/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.qmd" "NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf"

# 3. Track 2
render_and_move "docs/research/track_2_earthquake_prediction/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd" "EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.pdf"

# 4. Track 3
render_and_move "docs/research/track_3_gold_market/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.qmd" "GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.pdf"

# 5. Manuscripts
render_and_move "reports/manuscript.qmd" "manuscript_nature.pdf"

# For IEEE, we need to specify CSL. 
# We'll just run the command directly for this one to handle the extra arg
echo "Rendering manuscript_ieee.pdf..."
quarto render reports/manuscript.qmd --to pdf -M csl=reports/styles/ieee.csl -o manuscript_ieee.pdf
mv manuscript_ieee.pdf pdfs/
echo "✅ Moved manuscript_ieee.pdf to pdfs/"

echo "🎉 All PDFs generated in pdfs/ directory."
ls -lh pdfs/
