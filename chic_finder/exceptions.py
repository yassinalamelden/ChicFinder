class ChicFinderError(Exception):
    """Base Exception for ChicFinder"""
    pass

class AIError(ChicFinderError):
    """Exception raised for errors in the AI engine"""
    pass

class APIError(ChicFinderError):
    """Exception raised for errors in the API layer"""
    pass

class ConfigError(ChicFinderError):
    """Exception raised for configuration-related errors"""
    pass
