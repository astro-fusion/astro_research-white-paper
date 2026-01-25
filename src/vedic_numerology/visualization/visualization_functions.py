def visualize_planetary_strength_and_numerology():
    # Load the research results
    with open('research_results.json', 'r') as f:
        results = json.load(f)

    # Prepare data for visualization
    planet_strengths = {
        'Mars': results['astrology']['mars_dignity']['score'],
        'Venus': results['astrology']['venus_dignity']['score'],
    }

    numerology_values = {
        'Mulanka': results['numerology']['mulanka']['number'],
        'Bhagyanka': results['numerology']['bhagyanka']['number'],
    }

    # Call the visualization function
    plot_planetary_strength_numerology(
        chart=None,  # Replace with actual chart object if needed
        planet_strengths=planet_strengths,
        numerology_values=numerology_values,
        use_plotly=True
    )
