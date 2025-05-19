from typing import Any
import yaml
from griptape_nodes.exe_types.node_types import DataNode
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode, ParameterTypeBuiltin
from griptape.artifacts import TextArtifact

class YAMLLoaderNode(DataNode):
    def __init__(self, name: str, metadata: dict[Any, Any] | None = None) -> None:
        super().__init__(name, metadata)
        
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
                    "is_full_width": True,
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

    def process(self) -> None:
        """Process the YAML file and create output parameters."""
        yaml_file = self.get_parameter_value("yaml_file")
        key_filter = self.get_parameter_value("key_filter")
        
        if yaml_file is None:
            self.parameter_values["status_message"] = "No YAML file specified"
            return

        try:
            # Load the YAML file
            with open(yaml_file, 'r') as file:
                yaml_data = yaml.safe_load(file)

            if not isinstance(yaml_data, dict):
                self.parameter_values["status_message"] = "YAML file must contain a dictionary at the root level"
                return

            # Flatten the YAML structure
            flattened_items = self._flatten_yaml(yaml_data)
            
            # Filter items if key_filter is provided
            if key_filter:
                flattened_items = {k: v for k, v in flattened_items.items() if key_filter.lower() in k.lower()}
            
            # Track which parameters we want to keep
            valid_parameter_names = {"yaml_file", "yaml_data", "status_message", "key_filter"}
            
            # First, purge any old parameters that are no longer needed
            self._purge_old_parameters(valid_parameter_names)
            
            # Create or update parameters for each flattened key
            used_names = set()
            for key, value in flattened_items.items():
                base_name = f"output_{key}"
                param_name = base_name
                counter = 1
                
                while param_name in used_names:
                    param_name = f"{base_name}_{counter}"
                    counter += 1
                
                used_names.add(param_name)
                valid_parameter_names.add(param_name)
                
                # Create the parameter if it doesn't exist
                if not self.does_name_exist(param_name):
                    kwargs = {
                        "name": param_name,
                        "tooltip": f"Value for {key}",
                        "type": "str",
                        "allowed_modes": {ParameterMode.OUTPUT},
                        "ui_options": {
                            "display_name": key
                        },
                        "user_defined": False,
                        "settable": False
                    }
                    self.add_parameter(Parameter(**kwargs))
                
                # Update the value
                self.parameter_output_values[param_name] = str(value)
            
            # Update yaml_data output after all parameters are created
            self.parameter_output_values["yaml_data"] = yaml.dump(flattened_items, default_flow_style=False)
            
            self.parameter_values["status_message"] = "YAML file loaded successfully"

        except Exception as e:
            self.parameter_values["status_message"] = f"Error loading YAML file: {str(e)}"
            raise

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

            try:
                # Load and process YAML
                with open(yaml_file, 'r') as file:
                    yaml_data = yaml.safe_load(file)

                if not isinstance(yaml_data, dict):
                    self.parameter_values["status_message"] = "YAML file must contain a dictionary at the root level"
                    modified_parameters_set.add("status_message")
                    return

                # Flatten and filter the YAML structure
                flattened_items = self._flatten_yaml(yaml_data)
                if key_filter:
                    flattened_items = {k: v for k, v in flattened_items.items() if key_filter.lower() in k.lower()}
                
                # Track which parameters we want to keep
                valid_parameter_names = {"yaml_file", "yaml_data", "status_message", "key_filter"}
                
                # First, purge any old parameters that are no longer needed
                self._purge_old_parameters(valid_parameter_names)
                
                # Create or update parameters for each flattened key
                used_names = set()
                for key, value in flattened_items.items():
                    base_name = f"output_{key}"
                    param_name = base_name
                    counter = 1
                    
                    while param_name in used_names:
                        param_name = f"{base_name}_{counter}"
                        counter += 1
                    
                    used_names.add(param_name)
                    valid_parameter_names.add(param_name)
                    
                    # Create the parameter if it doesn't exist
                    if not self.does_name_exist(param_name):
                        kwargs = {
                            "name": param_name,
                            "tooltip": f"Value for {key}",
                            "type": "str",
                            "allowed_modes": {ParameterMode.OUTPUT},
                            "ui_options": {
                                "display_name": key
                            },
                            "user_defined": False,
                            "settable": False
                        }
                        self.add_parameter(Parameter(**kwargs))
                    
                    # Update the value
                    self.parameter_output_values[param_name] = str(value)
                    modified_parameters_set.add(param_name)
                
                # Update yaml_data output after all parameters are created
                self.parameter_output_values["yaml_data"] = yaml.dump(flattened_items, default_flow_style=False)
                modified_parameters_set.add("yaml_data")
                
                self.parameter_values["status_message"] = "YAML file loaded successfully"
                modified_parameters_set.add("status_message")

            except Exception as e:
                self.parameter_values["status_message"] = f"Error loading YAML file: {str(e)}"
                modified_parameters_set.add("status_message")
                raise
                
        elif parameter.name == "status_message":
            modified_parameters_set.add("status_message")