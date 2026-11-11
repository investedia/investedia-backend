"""Exact source statuses only. Absence and unknown values never imply operational."""
STATUS = {'proposed': 'Proposed', 'announced': 'Proposed', 'pre-permit': 'Proposed',
          'approved': 'Approved', 'permitted': 'Approved', 'pre-construction': 'Approved',
          'under construction': 'Under construction', 'construction': 'Under construction',
          'operational': 'Operational', 'operating': 'Operational', 'in service': 'Operational',
          'on hold': 'On hold', 'shelved': 'On hold', 'mothballed': 'On hold',
          'cancelled': 'Cancelled', 'canceled': 'Cancelled',
          'decommissioned': 'Decommissioned', 'retired': 'Decommissioned'}

def normalize(value):
    return STATUS.get(str(value or '').strip().casefold())
