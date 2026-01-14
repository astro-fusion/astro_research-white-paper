Testing
=======

The Vedic Numerology-Astrology Integration System includes comprehensive testing to ensure code quality and reliability.

Test Structure
--------------

Tests are organized by functionality:

.. code-block::

   tests/
   ├── test_numerology.py      # Numerology calculations
   ├── test_astrology.py       # Astrology calculations
   ├── test_dignity.py         # Dignity scoring
   ├── test_integration.py     # Integration tests
   └── test_visualization.py   # Visualization tests

Running Tests
-------------

**Run all tests:**

.. code-block:: bash

   pytest

**Run with coverage:**

.. code-block:: bash

   pytest --cov=vedic_numerology --cov-report=html

**Run specific test file:**

.. code-block:: bash

   pytest tests/test_numerology.py

**Run specific test:**

.. code-block:: bash

   pytest tests/test_numerology.py::TestNumerologyCalculations::test_calculate_mulanka

**Run tests matching pattern:**

.. code-block:: bash

   pytest -k "mulanka"

Test Types
----------

**Unit Tests**
   Test individual functions and methods in isolation.

.. code-block:: python

   def test_calculate_mulanka_basic(self):
       """Test basic Mulanka calculation."""
       calc = NumerologyCalculator()
       result = calc.calculate_mulanka("1984-08-27")
       assert result["number"] == 9
       assert result["planet"] == "Mars"

**Integration Tests**
   Test interactions between different components.

.. code-block:: python

   def test_full_analysis_workflow(self):
       """Test complete analysis workflow."""
       vna = VedicNumerologyAstrology("1984-08-27", "10:30", 28.6139, 77.1025)
       result = vna.analyze_support_contradiction()
       assert "mulanka" in result
       assert "bhagyanka" in result

**Reference Tests**
   Validate against known astronomical and numerological data.

.. code-block:: python

   @pytest.mark.parametrize("birth_date,expected_mulanka", [
       ("1984-08-27", 9),  # Mars
       ("1990-05-15", 3),  # Jupiter
       ("1975-01-11", 2),  # Moon
   ])
   def test_mulanka_reference_cases(self, birth_date, expected_mulanka):
       """Test against reference numerological cases."""
       calc = NumerologyCalculator()
       result = calc.calculate_mulanka(birth_date)
       assert result["number"] == expected_mulanka

Test Coverage
-------------

**Coverage Goals:**
- Minimum 90% code coverage
- All public APIs tested
- Edge cases covered
- Error conditions tested

**Coverage Report:**
Generated automatically with each test run. View at ``htmlcov/index.html``.

Writing Tests
-------------

**Test File Structure:**

.. code-block:: python

   import pytest
   from vedic_numerology.calculator import NumerologyCalculator

   class TestNumerologyCalculations:
       """Test cases for numerology calculations."""

       def setup_method(self):
           """Set up test fixtures."""
           self.calculator = NumerologyCalculator()

       def test_calculate_mulanka_valid_input(self):
           """Test Mulanka calculation with valid input."""
           result = self.calculator.calculate_mulanka("1984-08-27")
           assert isinstance(result, dict)
           assert "number" in result
           assert "planet" in result

       def test_calculate_mulanka_invalid_input(self):
           """Test Mulanka calculation with invalid input."""
           with pytest.raises(ValueError):
               self.calculator.calculate_mulanka("invalid-date")

**Best Practices:**

- Use descriptive test names
- Test one thing per test method
- Include docstrings explaining test purpose
- Use fixtures for common setup
- Parameterize tests for multiple inputs
- Mock external dependencies
- Test error conditions

Continuous Integration
----------------------

Tests run automatically on:

- Every push to main/develop branches
- All pull requests
- Manual workflow dispatch

**CI Pipeline:**
1. Code quality checks (Black, isort, flake8, mypy)
2. Security scanning (Bandit, Safety)
3. Test execution with coverage
4. Documentation building
5. Manuscript compilation

Debugging Test Failures
-----------------------

**Common Issues:**

1. **Import Errors:**
   - Check PYTHONPATH
   - Verify package installation

2. **Swiss Ephemeris Errors:**
   - Ensure ephemeris files are available
   - Check system library installation

3. **Path Issues:**
   - Use absolute paths in tests
   - Check working directory

4. **Floating Point Precision:**
   - Use ``pytest.approx()`` for floating point comparisons
   - Define appropriate tolerances

**Debug Commands:**

.. code-block:: bash

   # Run test with debug output
   pytest -v -s tests/test_numerology.py::TestNumerologyCalculations::test_calculate_mulanka

   # Run with Python debugger
   pytest --pdb tests/failing_test.py

   # Run tests in parallel for speed
   pytest -n auto

Performance Testing
-------------------

**Benchmark Tests:**

.. code-block:: python

   import time
   import pytest

   def test_analysis_performance(benchmark):
       """Test analysis performance."""
       vna = VedicNumerologyAstrology("1984-08-27", "10:30", 28.6139, 77.1025)

       # Benchmark the analysis function
       result = benchmark(vna.analyze_support_contradiction)

       # Assert reasonable performance
       assert result is not None
       assert benchmark.stats.mean < 1.0  # Should complete in < 1 second

**Load Testing:**
- Test with large datasets
- Memory usage monitoring
- Concurrent analysis testing

Test Maintenance
----------------

**Keeping Tests Current:**

1. **Update Reference Data:** When algorithms change, update expected results
2. **Add New Tests:** For new features, add corresponding tests
3. **Remove Obsolete Tests:** Clean up tests for removed features
4. **Review Coverage:** Ensure new code is adequately tested

**Test Organization:**

- Group related tests in classes
- Use descriptive naming conventions
- Keep test files focused on specific functionality
- Use fixtures for common test data
- Document complex test scenarios