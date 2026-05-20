# Nexus Digital Identity Management System

A robust backend system for managing digital identities across a federated ecosystem of organisations. Built as part of the Software Engineering Project.

## 🔗 Repository

**GitHub Repository:** [Add your repository link here]

## 📋 Overview

The Nexus Digital ID platform enables a central authority to manage digital identities whilst allowing authorised consuming organisations to verify and access limited identity information through dedicated portals.

### Key Features

- **Identity Lifecycle Management**: Create, update, and manage Digital ID status (Active, Suspended, Revoked)
- **Organisation Portals**: Tiered access levels (Basic, Standard, Enhanced) for consuming organisations
- **Verification Services**: Specialised verification for tax authorities, driving licence authorities, employers, and banks
- **Comprehensive Audit Trail**: All operations logged with timestamps and actor information
- **Deterministic Operations**: Consistent state management with idempotent operations

## 🏗️ System Architecture

```
nexus_digital_id/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── identity_vault.py      # Digital ID data model and storage
│   ├── status_sentinel.py     # Status management service
│   └── attribute_keeper.py    # Attribute management service
├── authority/
│   ├── __init__.py
│   ├── central_command.py     # Central Authority operations
│   └── org_registry.py        # Organisation registration
├── verification/
│   ├── __init__.py
│   ├── portal_gateway.py      # Verification service router
│   ├── tax_verifier.py        # Tax authority verification
│   ├── dvla_verifier.py       # Driving licence verification
│   └── basic_verifier.py      # Basic validity checks
├── compliance/
│   ├── __init__.py
│   ├── audit_chronicle.py     # Audit logging system
│   ├── rule_enforcer.py       # Business rules engine
│   └── request_sentinel.py    # Request validation
├── interface/
│   ├── __init__.py
│   └── command_deck.py        # Console interface
└── exceptions/
    ├── __init__.py
    └── nexus_errors.py        # Custom exceptions

tests/
├── __init__.py
├── test_identity_vault.py
├── test_status_sentinel.py
├── test_attribute_keeper.py
├── test_central_command.py
├── test_org_registry.py
├── test_verification_services.py
├── test_audit_chronicle.py
├── test_rule_enforcer.py
├── test_request_sentinel.py
├── test_command_deck.py
└── conftest.py                # Shared fixtures
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd Task20
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the System

**Interactive Console Mode:**
```bash
python -m nexus_digital_id
```

**Execute Single Command:**
```bash
python -m nexus_digital_id --command "create-id --name 'John Smith' --dob 1990-05-15 --pob London --nationality GBR"
```

**Batch Processing:**
```bash
python -m nexus_digital_id --batch operations.json
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=nexus_digital_id --cov-report=html

# Run specific test file
pytest tests/test_identity_vault.py -v
```

## 📖 Usage Examples

### Creating a Digital ID (Central Authority)
```
nexus> create-id --name "Eleanor Vance" --dob 1985-03-22 --pob Manchester --nationality GBR --address "42 Willow Lane, Bristol" --email eleanor.vance@email.co.uk --phone +447700900123
```

### Updating an Attribute
```
nexus> update-attr --id DID-7f3a9b2c --attr address --value "15 Oak Street, London"
```

### Changing Status
```
nexus> change-status --id DID-7f3a9b2c --status SUSPENDED
```

### Verification (as Organisation)
```
nexus> verify --id DID-7f3a9b2c --org HMRC --type tax --period-start 2023-04-06 --period-end 2024-04-05
```

## 🔐 Access Levels

| Level | Organisations | Capabilities |
|-------|--------------|--------------|
| BASIC | Employers, Banks | Validity check only |
| STANDARD | Local Authorities, Welfare | Validity + limited attributes |
| ENHANCED | Tax (HMRC), DVLA, Immigration | Full verification with history |

## 🧪 Testing Strategy

- **Unit Tests**: All core components tested in isolation
- **Integration Tests**: Service interaction verification
- **Property-Based Tests**: Deterministic behaviour validation using Hypothesis
- **Coverage Target**: Minimum 80% line coverage

## 📊 Continuous Integration

GitHub Actions workflow automatically:
- Runs full test suite on push/PR
- Checks code style with flake8
- Generates coverage reports
- Fails build if coverage < 80%

## 👤 Author

Hussarim - Queen Mary University of London

## 📄 Licence

This project is submitted as coursework for ECS506U Software Engineering Project.
