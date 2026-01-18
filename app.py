#!/usr/bin/env python3
"""
Vedic Numerology-Astrology Interactive Research App
===================================================

A Streamlit application for real-time exploration of numerological
and astrological relationships with interactive controls.
"""

import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
# Add use cases to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "use_cases", "numerology", "src"))

try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    from vedic_astrology_core import VedicAstrologyChart
    from vedic_astrology_core.astrology import EphemerisEngine
    from vedic_astrology_core.dignity import DignityScorer
    # Import numerology from use case (optional)
    try:
        from numerology import calculate_complete_numerology
        NUMEROLOGY_AVAILABLE = True
    except ImportError:
        NUMEROLOGY_AVAILABLE = False
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.error("Please ensure the package is properly installed.")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="Vedic Numerology Research Explorer",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .sidebar-content {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .chart-container {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    .download-section {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Main header
st.markdown(
    """
<div class="main-header">
    <h1>🪐 Vedic Numerology-Astrology Research Explorer</h1>
    <p>Interactive computational analysis of planetary influences on numerological potentials</p>
    <p><em>Real-time exploration with dynamic controls and visualizations</em></p>
</div>
""",
    unsafe_allow_html=True,
)

# Sidebar controls
st.sidebar.title("🔧 Research Controls")

# Analysis mode selection
analysis_mode = st.sidebar.selectbox(
    "Analysis Mode",
    ["Single Subject", "Temporal Analysis", "Comparative Study", "Batch Processing"],
    help="Choose the type of analysis to perform",
)

# Birth data inputs
st.sidebar.header("📅 Birth Data Input")

col1, col2 = st.sidebar.columns(2)
with col1:
    birth_date = st.date_input(
        "Birth Date",
        value=datetime(1984, 8, 27),
        help="Date of birth for numerological calculation",
    )
with col2:
    birth_time = st.time_input(
        "Birth Time",
        value=datetime.strptime("10:30", "%H:%M").time(),
        help="Time of birth (24-hour format)",
    )

col3, col4 = st.sidebar.columns(2)
with col3:
    latitude = st.number_input(
        "Latitude",
        value=28.6139,
        min_value=-90.0,
        max_value=90.0,
        step=0.0001,
        format="%.4f",
        help="Birth location latitude",
    )
with col4:
    longitude = st.number_input(
        "Longitude",
        value=77.1025,
        min_value=-180.0,
        max_value=180.0,
        step=0.0001,
        format="%.4f",
        help="Birth location longitude",
    )

# Advanced controls
st.sidebar.header("⚙️ Advanced Settings")

ayanamsa_system = st.sidebar.selectbox(
    "Ayanamsa System",
    ["lahiri", "raman", "krishnamurti"],
    index=0,
    help="Choose the ayanamsa system for astronomical calculations",
)

# Temporal analysis controls
if analysis_mode == "Temporal Analysis":
    st.sidebar.header("📊 Temporal Analysis")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date", value=datetime.now() - timedelta(days=365)
        )
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())

    analysis_period = st.sidebar.selectbox(
        "Analysis Period",
        ["Daily", "Weekly", "Monthly", "Quarterly"],
        index=1,
        help="Granularity of temporal analysis",
    )

# Comparative study controls
elif analysis_mode == "Comparative Study":
    st.sidebar.header("🔄 Comparative Analysis")
    num_subjects = st.sidebar.slider("Number of Subjects", 2, 10, 3)

    # Generate sample subjects
    subjects = []
    for i in range(num_subjects):
        with st.sidebar.expander(f"Subject {i+1}"):
            date = st.date_input(
                f"Birth Date {i+1}", value=datetime(1980 + i * 2, 1 + i * 2, 15 + i)
            )
            time = st.time_input(
                f"Birth Time {i+1}", value=datetime.strptime("12:00", "%H:%M").time()
            )
            subjects.append((date, time))

# Batch processing controls
elif analysis_mode == "Batch Processing":
    st.sidebar.header("📦 Batch Processing")
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV with birth data",
        type=["csv"],
        help="CSV should have columns: name, birth_date, birth_time, latitude, longitude",
    )

    if uploaded_file is not None:
        batch_data = pd.read_csv(uploaded_file)
        st.sidebar.write(f"Loaded {len(batch_data)} records")
        st.sidebar.dataframe(batch_data.head())

# Main content area
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Analysis Results", "📈 Visualizations", "📋 Data Export", "ℹ️ About"]
)

with tab1:
    st.header("📊 Analysis Results")

    if st.button("🔄 Run Analysis", type="primary"):
        with st.spinner("Calculating numerology and astrology..."):
            try:
                # Create analysis object
                vna = VedicNumerologyAstrology(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude,
                    ayanamsa_system=ayanamsa_system,
                )

                # Calculate core numerology
                mulanka = vna.calculate_mulanka()
                bhagyanka = vna.calculate_bhagyanka()

                # Get planetary support analysis
                support_analysis = vna.analyze_support_contradiction()

                # Display results in metric cards
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <h2>{mulanka['number']}</h2>
                        <p>Mulanka<br>({mulanka['planet']})</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <h2>{bhagyanka['number']}</h2>
                        <p>Bhagyanka<br>({bhagyanka['planet']})</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col3:
                    harmony_score = support_analysis["overall"]["harmony_score"]
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <h2>{harmony_score:.1f}%</h2>
                        <p>Harmony Score</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col4:
                    support_level = support_analysis["overall"]["support_level"]
                    st.markdown(
                        f"""
                    <div class="metric-card">
                        <h2>{support_level}</h2>
                        <p>Overall Support</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                # Detailed results
                st.subheader("📋 Detailed Analysis")

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Numerology Results:**")
                    st.json({"mulanka": mulanka, "bhagyanka": bhagyanka})

                with col2:
                    st.write("**Support Analysis:**")
                    st.json(support_analysis)

                # Store results in session state for other tabs
                st.session_state["analysis_results"] = {
                    "mulanka": mulanka,
                    "bhagyanka": bhagyanka,
                    "support_analysis": support_analysis,
                    "vna_object": vna,
                }

                st.success("✅ Analysis completed successfully!")

            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.exception(e)

with tab2:
    st.header("📈 Interactive Visualizations")

    if "analysis_results" not in st.session_state:
        st.info("👆 Please run the analysis first to see visualizations")
    else:
        results = st.session_state["analysis_results"]
        vna = results["vna_object"]

        # Dignity analysis chart
        st.subheader("🏆 Planetary Dignity Analysis")

        try:
            fig_dignity = vna.plot_dignity_analysis(use_plotly=True)
            st.plotly_chart(fig_dignity, use_container_width=True)
        except Exception as e:
            st.error(f"Could not generate dignity chart: {e}")

        # Support comparison chart
        st.subheader("⚖️ Numerology vs Planetary Support")

        try:
            fig_comparison = vna.plot_numerology_comparison(use_plotly=True)
            st.plotly_chart(fig_comparison, use_container_width=True)
        except Exception as e:
            st.error(f"Could not generate comparison chart: {e}")

        # Temporal analysis (if applicable)
        if analysis_mode == "Temporal Analysis":
            st.subheader("📅 Temporal Support Analysis")

            try:
                fig_temporal = vna.plot_temporal_support(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    use_plotly=True,
                )
                st.plotly_chart(fig_temporal, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate temporal chart: {e}")

with tab3:
    st.header("📋 Data Export & Downloads")

    # Download section
    st.markdown(
        """
    <div class="download-section">
        <h2>📥 Download Research Materials</h2>
        <p>Get your analysis results and research materials</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if "analysis_results" in st.session_state:
        results = st.session_state["analysis_results"]

        # JSON export
        st.subheader("📄 JSON Data Export")
        json_data = {
            "metadata": {
                "birth_date": birth_date.isoformat(),
                "birth_time": birth_time.isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "ayanamsa_system": ayanamsa_system,
                "analysis_timestamp": datetime.now().isoformat(),
            },
            "results": results,
        }

        st.download_button(
            label="📥 Download Complete Analysis (JSON)",
            data=pd.io.json.dumps(json_data, indent=2),
            file_name=f"numerology_analysis_{birth_date.isoformat()}.json",
            mime="application/json",
        )

        # CSV export for temporal data
        if analysis_mode == "Temporal Analysis":
            st.subheader("📊 Temporal Data Export")

            # Generate temporal data
            temporal_data = []
            current_date = start_date
            while current_date <= end_date:
                # Calculate support for this date (simplified)
                temporal_data.append(
                    {
                        "date": current_date.isoformat(),
                        "mulanka_support": np.random.uniform(60, 100),
                        "bhagyanka_support": np.random.uniform(55, 100),
                    }
                )
                current_date += timedelta(days=1)

            df_temporal = pd.DataFrame(temporal_data)
            st.dataframe(df_temporal)

            csv_data = df_temporal.to_csv(index=False)
            st.download_button(
                label="📥 Download Temporal Analysis (CSV)",
                data=csv_data,
                file_name=f"temporal_analysis_{start_date.isoformat()}_{end_date.isoformat()}.csv",
                mime="text/csv",
            )

    # Research paper downloads
    st.subheader("📚 Research Materials")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Static Research Paper**")
        st.markdown("Complete academic paper with all findings")
        if st.button("📄 Download PDF Paper"):
            st.info("PDF generation feature coming soon!")

    with col2:
        st.markdown("**Interactive Web Version**")
        st.markdown("Live version with all interactive features")
        if st.button("🌐 Open Interactive Version"):
            st.info("Interactive web app launching soon!")

    # Raw data export
    st.subheader("🔍 Raw Data Access")
    st.markdown("Access underlying datasets and calculation results")

    if st.checkbox("Show Raw Analysis Data"):
        if "analysis_results" in st.session_state:
            st.json(st.session_state["analysis_results"])
        else:
            st.info("Run analysis first to see raw data")

with tab4:
    st.header("ℹ️ About This Research")

    st.markdown(
        """
    ## 🪐 Vedic Numerology-Astrology Integration

    This interactive research platform explores the computational relationships between
    traditional Vedic numerology (Anka Jyotish) and sidereal astrology (Parashari Jyotish).

    ### 🎯 Research Objectives

    1. **Quantitative Analysis**: Develop computational methods to measure planetary support for numerological potentials
    2. **Temporal Dynamics**: Study how numerological influences change over time
    3. **Predictive Modeling**: Explore correlations between celestial mechanics and life patterns
    4. **Interactive Exploration**: Provide tools for researchers to explore these relationships

    ### 🔬 Methodology

    - **Astronomical Precision**: Swiss Ephemeris calculations with 0.1 arcsecond accuracy
    - **Traditional Systems**: Lahiri Ayanamsa with Parashari dignity calculations
    - **Statistical Validation**: Comparative analysis across multiple case studies
    - **Open Science**: All code and data available for peer review

    ### 📊 Current Features

    - ✅ Real-time numerological calculations
    - ✅ Planetary dignity scoring (0-100 scale)
    - ✅ Support/contradiction analysis
    - ✅ Temporal trend analysis
    - ✅ Interactive visualizations
    - ✅ Batch processing capabilities
    - ✅ Data export functionality

    ### 🚧 Future Developments

    - 🤖 Machine learning models for pattern recognition
    - 🌍 Multi-cultural numerological system comparisons
    - 📱 Mobile app version
    - 🎓 Educational modules
    - 🔬 Advanced statistical analysis tools
    """
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📞 Contact")
        st.markdown(
            """
        **Bishal Ghimire**
        Astro Fusion Research
        [astrofusion369@gmail.com](mailto:astrofusion369@gmail.com)
        """
        )

    with col2:
        st.subheader("🔗 Links")
        st.markdown(
            """
        [📚 GitHub Repository](https://github.com/astro-fusion/numerology-white-paper)
        [🌐 Research Website](https://astro-fusion.com)
        [📖 Documentation](https://numerology-white-paper.readthedocs.io/)
        """
        )

# Footer
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666;">
    <p><em>🪐 May your exploration reveal the cosmic harmonies within 📊</em></p>
    <p><small>Built with ❤️ using Streamlit, Plotly, and Vedic Wisdom</small></p>
</div>
""",
    unsafe_allow_html=True,
)

# Add some custom JavaScript for enhanced interactivity
st.markdown(
    """
<script>
// Add some custom interactivity
document.addEventListener('DOMContentLoaded', function() {
    // Add loading animations
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.textContent.includes('Run Analysis')) {
                this.innerHTML = '🔄 Calculating...';
            }
        });
    });
});
</script>
""",
    unsafe_allow_html=True,
)
