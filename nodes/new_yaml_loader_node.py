from typing import Any
import yaml
from griptape_nodes.exe_types.node_types import DataNode
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode, ParameterTypeBuiltin
from griptape.artifacts import TextArtifact
import time

class NEW_YAMLLoaderNode(DataNode):
    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)

        self.yaml_dictionary = {}
        self.yaml_list = []
        
        # Input parameter for YAML file
        self.add_parameter(
            Parameter(
                name="yaml_file",
                tooltip="Path to the YAML file to load",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={
                    "display_name": "YAML File Path",
                    "clickable_file_browser": True
                }
            )
        )

        # Filter parameter
        self.add_parameter(
            Parameter(
                name="key_filter",
                tooltip="Optional filter to only include keys containing this text",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={
                    "display_name": "Key Filter",
                    "placeholder_text": "Leave empty to show all keys"
                }
            )
        )

        # Output parameter for the YAML data
        self.add_parameter(
            Parameter(
                name="yaml_data",
                tooltip="YAML data",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.OUTPUT},
                ui_options={
                    "display_name": "YAML Data",
                    "multiline": True,
                    "is_full_width": False,
                    "className": "scrollable-text"
                }
            )
        )

        # Status message parameter
        self.add_parameter(
            Parameter(
                name="status_message",
                tooltip="Status messages about the YAML loading process",
                type=ParameterTypeBuiltin.STR.value,
                allowed_modes={ParameterMode.PROPERTY},
                ui_options={
                    "multiline": True,
                    "hide": True
                }
            )
        )

    def _flatten_yaml(self, data: dict, parent_key: str = '', sep: str = '.') -> dict:
        """Flatten a nested dictionary with dot notation."""
        items = []
        for k, v in data.items():
            # Replace whitespace with underscore in key names
            k = str(k).replace(' ', '_')
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_yaml(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Handle lists by creating numbered keys
                for i, item in enumerate(v, 1):
                    if isinstance(item, dict):
                        # For each item in the list, create a key with the index
                        for sub_k, sub_v in item.items():
                            sub_k = str(sub_k).replace(' ', '_')
                            list_key = f"{new_key}[{i}].{sub_k}"
                            items.append((list_key, sub_v))
                    else:
                        # If the list item is not a dict, just add it with the index
                        items.append((f"{new_key}[{i}]", item))
            else:
                items.append((new_key, v))
        return dict(items)

    def _load_yaml_file(self, file_path: str) -> Any:
        """Load a YAML file and return its content as a list or dictionary."""
        try:
            with open(file_path, 'r') as file:
                yaml_data = yaml.safe_load(file)

            if isinstance(yaml_data, dict):
                return yaml_data
            elif isinstance(yaml_data, list):
                return yaml_data
            else:
                raise ValueError("YAML file must contain a dictionary or a list at the root level")
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {file_path} was not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred while loading the YAML file: {e}")

    def process(self) -> None:
        """Do nothing. All actions are handled in the after_value_set method."""
        return

    def _purge_old_parameters(self, valid_parameter_names: set[str]) -> set[str]:
        # Always maintain these parameters
        valid_parameter_names.update([
            "yaml_file",
            "yaml_data",
            "status_message"
        ])

        modified_parameters_set = set()
        for param in self.parameters:
            if param.name not in valid_parameter_names:
                self.remove_parameter_element(param)
                modified_parameters_set.add(param.name)
        return modified_parameters_set

    def after_value_set(self, parameter: Parameter, value: Any, modified_parameters_set: set[str]) -> None:
        """Callback after a value has been set on this Node."""
        if parameter.name in ["yaml_file", "key_filter"]:
            # Get current values
            yaml_file = self.get_parameter_value("yaml_file")
            key_filter = self.get_parameter_value("key_filter")
            
            if yaml_file is None:
                self.parameter_values["status_message"] = "No YAML file specified"
                modified_parameters_set.add("status_message")
                return

            # Load the YAML file using the new method
            yaml_data = self._load_yaml_file(yaml_file)

            # Store the loaded YAML in the appropriate class variable
            if isinstance(yaml_data, dict):
                self.yaml_dictionary = yaml_data
            elif isinstance(yaml_data, list):
                self.yaml_list = yaml_data

            # Flatten and filter the YAML structure if it's a dictionary
            if self.yaml_dictionary:
                self.yaml_list = self._flatten_yaml(self.yaml_dictionary)
                
            if key_filter:
                self.yaml_list = {k: v for k, v in self.yaml_list.items() if key_filter.lower() in k.lower()}

            # After processing and filtering the YAML data, set the yaml_data parameter
            self.set_parameter_value("yaml_data", yaml.dump(self.yaml_list, default_flow_style=False))
            modified_parameters_set.add("yaml_data")

            # Iterate through the items in self.yaml_list
            valid_parameter_names = {"yaml_file", "yaml_data", "status_message", "key_filter"}
            used_names = set()

            for index, item in enumerate(self.yaml_list, start=1):
                param_name = f"{index}_{item}"
                used_names.add(param_name)
                valid_parameter_names.add(param_name)

                # Create the parameter if it doesn't exist
                if not self.does_name_exist(param_name):
                    kwargs = {
                        "name": param_name,
                        "type": "str",
                        "allowed_modes": {ParameterMode.OUTPUT},
                        "ui_options": {
                            "display_name": param_name
                        },
                        "tooltip": param_name,
                        "user_defined": False,
                        "settable": False
                    }
                    self.add_parameter(Parameter(**kwargs))

                # Update the value
                self.set_parameter_value(param_name, self.yaml_list[item])            
                modified_parameters_set.add(param_name)

            # Remove any parameters that are not in the list
            purged_params = self._purge_old_parameters(valid_parameter_names)

            for param in purged_params:
                modified_parameters_set.add(param)

            return modified_parameters_set
        