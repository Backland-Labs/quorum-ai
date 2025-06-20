from importlib import import_module as _imp

# Re-export commonly patched services for test suite compatibility

_tally = _imp('services.tally_service')
_ai = _imp('services.ai_service')

# Public re-exports so `api.tally_service` etc. resolve

globals()['tally_service'] = _tally
globals()['ai_service'] = _ai

__all__ = ['tally_service', 'ai_service']