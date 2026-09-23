"""
Configuration Management Module

This module provides a comprehensive configuration management system for the
application. It leverages the factory pattern to create appropriate configuration
loaders and utilizes the builder pattern to construct configuration objects
in a flexible and maintainable manner.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ApplicationConfiguration:
    """Represents the complete application configuration.

    Attributes:
        database_host: The hostname of the database server.
        database_port: The port number for database connections.
        database_name: The name of the database to connect to.
        enable_debug_mode: Whether to enable debug mode.
        log_level: The logging level for the application.
        max_connection_pool_size: Maximum number of connections in the pool.
    """
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "app_db"
    enable_debug_mode: bool = False
    log_level: str = "INFO"
    max_connection_pool_size: int = 10


class ApplicationConfigurationBuilder:
    """Builder for constructing ApplicationConfiguration objects.

    This builder provides a fluent interface for setting configuration values,
    ensuring that the configuration is constructed in a clear and maintainable way.
    """

    def __init__(self):
        """Initialize the builder with default values."""
        self._configuration_values: Dict[str, object] = {}

    def with_database_host(self, host: str) -> "ApplicationConfigurationBuilder":
        """Set the database host."""
        self._configuration_values["database_host"] = host
        return self

    def with_database_port(self, port: int) -> "ApplicationConfigurationBuilder":
        """Set the database port."""
        self._configuration_values["database_port"] = port
        return self

    def with_database_name(self, name: str) -> "ApplicationConfigurationBuilder":
        """Set the database name."""
        self._configuration_values["database_name"] = name
        return self

    def with_debug_mode(self, enabled: bool) -> "ApplicationConfigurationBuilder":
        """Enable or disable debug mode."""
        self._configuration_values["enable_debug_mode"] = enabled
        return self

    def build(self) -> ApplicationConfiguration:
        """Build and return the ApplicationConfiguration object."""
        return ApplicationConfiguration(**self._configuration_values)


class ConfigurationLoaderFactory:
    """Factory for creating appropriate configuration loaders.

    This factory implements the factory pattern to create the correct
    configuration loader based on the specified configuration source type.
    """

    @staticmethod
    def create_loader(source_type: str) -> "BaseConfigurationLoader":
        """Create a configuration loader for the given source type.

        Args:
            source_type: The type of configuration source (e.g., 'env', 'file').

        Returns:
            An appropriate configuration loader instance.

        Raises:
            ValueError: If the source type is not supported.
        """
        if source_type == "environment":
            return EnvironmentConfigurationLoader()
        elif source_type == "file":
            return FileConfigurationLoader()
        raise ValueError(
            f"Unsupported configuration source type: {source_type}. "
            f"Please use 'environment' or 'file'."
        )


class BaseConfigurationLoader:
    """Base class for all configuration loaders."""

    def load_configuration(self) -> ApplicationConfiguration:
        """Load and return the application configuration."""
        raise NotImplementedError(
            "Subclasses must implement the load_configuration method."
        )


class EnvironmentConfigurationLoader(BaseConfigurationLoader):
    """Loads configuration from environment variables."""

    def load_configuration(self) -> ApplicationConfiguration:
        """Load configuration from environment variables.

        Returns:
            ApplicationConfiguration: The loaded configuration.
        """
        import os

        builder = ApplicationConfigurationBuilder()
        builder.with_database_host(
            os.environ.get("DATABASE_HOST", "localhost")
        )
        builder.with_database_port(
            int(os.environ.get("DATABASE_PORT", "5432"))
        )
        builder.with_database_name(
            os.environ.get("DATABASE_NAME", "app_db")
        )
        builder.with_debug_mode(
            os.environ.get("DEBUG_MODE", "false").lower() == "true"
        )
        return builder.build()


class FileConfigurationLoader(BaseConfigurationLoader):
    """Loads configuration from a JSON file."""

    def load_configuration(self) -> ApplicationConfiguration:
        """Load configuration from a JSON configuration file.

        Returns:
            ApplicationConfiguration: The loaded configuration.
        """
        import json

        configuration_file_path = "config.json"
        with open(configuration_file_path, "r") as configuration_file:
            configuration_data = json.load(configuration_file)

        builder = ApplicationConfigurationBuilder()
        builder.with_database_host(
            configuration_data.get("database_host", "localhost")
        )
        builder.with_database_port(
            configuration_data.get("database_port", 5432)
        )
        builder.with_database_name(
            configuration_data.get("database_name", "app_db")
        )
        builder.with_debug_mode(
            configuration_data.get("enable_debug_mode", False)
        )
        return builder.build()
