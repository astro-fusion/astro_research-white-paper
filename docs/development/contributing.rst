Contributing
============

Thank you for your interest in contributing to the Vedic Numerology-Astrology Integration System!

Development Setup
-----------------

1. Fork the repository on GitHub
2. Clone your fork:

   .. code-block:: bash

      git clone https://github.com/YOUR_USERNAME/numerology-white-paper.git
      cd numerology-white-paper

3. Set up development environment:

   .. code-block:: bash

      make setup-dev

4. Run tests to ensure everything works:

   .. code-block:: bash

      make test

Code Style
----------

This project follows strict code quality standards:

**Python Code Style:**
- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

**Run quality checks:**

.. code-block:: bash

   make quality-gate

**Format code:**

.. code-block:: bash

   make format

Testing
-------

**Run all tests:**

.. code-block:: bash

   make test

**Run tests with coverage:**

.. code-block:: bash

   make test-cov

**Run specific tests:**

.. code-block:: bash

   pytest tests/test_numerology.py -v

Documentation
-------------

**Build documentation:**

.. code-block:: bash

   make docs

**Serve documentation locally:**

.. code-block:: bash

   make serve-docs

**Writing Documentation:**
- Use Google-style docstrings
- Include examples in docstrings
- Keep documentation up-to-date with code changes

Submitting Changes
------------------

1. Create a feature branch:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

2. Make your changes following the guidelines above

3. Run quality checks:

   .. code-block:: bash

      make quality-gate

4. Commit your changes:

   .. code-block:: bash

      git add .
      git commit -m "feat: add your feature description"

5. Push and create a pull request:

   .. code-block:: bash

      git push origin feature/your-feature-name

Pull Request Guidelines
-----------------------

- Include a clear description of changes
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Follow conventional commit format

Types of Contributions
----------------------

**Code Contributions:**
- Bug fixes
- New features
- Performance improvements
- Code refactoring

**Documentation:**
- Improve existing docs
- Add tutorials
- Create examples
- Fix typos

**Testing:**
- Add unit tests
- Integration tests
- Performance benchmarks

**Research:**
- Validate algorithms
- Add new calculation methods
- Improve accuracy

Reporting Issues
----------------

When reporting bugs or requesting features:

1. Check existing issues first
2. Use issue templates when available
3. Include:
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Code examples if applicable

Code of Conduct
---------------

This project follows a code of conduct that promotes:

- Respectful communication
- Inclusive language
- Constructive feedback
- Professional collaboration
- Ethical research practices